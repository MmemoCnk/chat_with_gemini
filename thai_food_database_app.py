import streamlit as st
import pandas as pd
import os
import json
import re
from io import StringIO
import requests

st.set_page_config(
    page_title="Thai Food Chatbot",
    page_icon="🍜",
    layout="wide"
)

# Initialize session state for storing dataframes
if 'dataframes' not in st.session_state:
    st.session_state.dataframes = {}
if 'data_dicts' not in st.session_state:
    st.session_state.data_dicts = {}
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Function to determine if file is a data dictionary
def is_data_dict(filename):
    return 'data_dict' in filename

# Function to generate response based on user question
def get_response_for_question(question, dishes_df, ingredients_df, recipe_df):
    # ตรวจสอบการดึงชื่ออาหาร และแสดงค่าเพื่อการดีบัก
    dish_name = extract_dish_name(question)
    print(f"DEBUG - คำถาม: {question}, ชื่ออาหารที่ดึงได้: {dish_name}")  # บันทึกลง log เพื่อดีบัก
    
    # สร้างโปรมต์สำหรับ Gemini (โค้ดเบื้องหลังไม่แสดงให้ผู้ใช้เห็น)
    prompt = generate_gemini_prompt(question, dishes_df, ingredients_df, recipe_df)
    
    # จำลองการตอบกลับสำหรับคำถามเกี่ยวกับแคลอรี่
    if "calories" in question.lower() or "แคลอรี" in question or "calorie" in question.lower():
        if dish_name:
            # ดึงข้อมูลจาก dataframe
            try:
                # หา dish_id
                dish_data = dishes_df[dishes_df['dish_name'].str.contains(dish_name, case=False, na=False)]
                
                if not dish_data.empty:
                    dish_id = dish_data.iloc[0]['dish_id']
                    dish_name_full = dish_data.iloc[0]['dish_name']
                    
                    # ดึงส่วนผสมทั้งหมด
                    ingredients_used = recipe_df[recipe_df['dish_id'] == dish_id]
                    
                    # คำนวณแคลอรี่โดยประมาณ
                    total_calories = 0
                    ingredient_details = []
                    
                    for _, row in ingredients_used.iterrows():
                        ingredient_id = row['ingredient_id']
                        ingredient_data = ingredients_df[ingredients_df['ingredient_id'] == ingredient_id]
                        
                        if not ingredient_data.empty:
                            ingredient_name = ingredient_data.iloc[0]['ingredient_name']
                            calories = ingredient_data.iloc[0]['calories_per_100g']
                            
                            # แปลงปริมาณเป็นตัวเลขถ้าเป็นไปได้
                            try:
                                amount = float(row['amount'])
                            except:
                                # กรณีไม่สามารถแปลงเป็นตัวเลขได้ กำหนดค่าโดยประมาณ
                                if str(row['amount']) == 'สำหรับทอด':
                                    amount = 50  # น้ำมันสำหรับทอด ประมาณ 50 กรัม
                                elif '/' in str(row['amount']):
                                    # กรณีเป็นเศษส่วน เช่น 1/2
                                    nums = str(row['amount']).split('/')
                                    amount = float(nums[0]) / float(nums[1])
                                else:
                                    amount = 10  # ค่าเริ่มต้น
                            
                            # คำนวณแคลอรี่ตามปริมาณที่ใช้
                            unit = row['unit']
                            if unit == 'กรัม':
                                ingredient_calories = (amount / 100) * float(calories)
                            elif unit in ['ช้อนโต๊ะ', 'ช้อนชา']:
                                # ประมาณน้ำหนักของวัตถุดิบต่อช้อน
                                weight_per_spoon = 15 if unit == 'ช้อนโต๊ะ' else 5
                                ingredient_calories = (amount * weight_per_spoon / 100) * float(calories)
                            else:
                                # กรณีหน่วยอื่นๆ ประมาณการ
                                ingredient_calories = (amount / 10) * float(calories)
                                
                            total_calories += ingredient_calories
                            ingredient_details.append(f"{ingredient_name}: {round(ingredient_calories)} แคลอรี่")
                    
                    # สร้างคำตอบ
                    response = f"""
{dish_name_full} มีแคลอรี่ประมาณ {round(total_calories)} แคลอรี่ต่อจาน

แคลอรี่จากวัตถุดิบหลัก:
- {chr(10).join(['- ' + item for item in ingredient_details[:5]])}

โปรดทราบว่านี่เป็นการประมาณการเท่านั้น ค่าแคลอรี่ที่แท้จริงอาจแตกต่างกันไปขึ้นอยู่กับขนาดของการเสิร์ฟและวิธีการปรุง
                    """
                    return response
                else:
                    return f"ขออภัย ไม่พบข้อมูลอาหารชื่อ '{dish_name}' ในฐานข้อมูล กรุณาตรวจสอบการสะกดชื่ออาหารและลองใหม่อีกครั้ง"
                    
            except Exception as e:
                return f"เกิดข้อผิดพลาดในการวิเคราะห์ข้อมูล: {str(e)}"
        else:
            return "กรุณาระบุชื่ออาหารที่ต้องการทราบแคลอรี่ เช่น 'แคลอรี่ของต้มยำกุ้ง'"
            
    # จำลองการตอบกลับสำหรับคำถามเกี่ยวกับส่วนผสม
    elif "ส่วนผสม" in question or "ingredients" in question.lower() or "วัตถุดิบ" in question:
        dish_name = extract_dish_name(question)
        if dish_name:
            try:
                # หา dish_id
                dish_data = dishes_df[dishes_df['dish_name'].str.contains(dish_name, case=False, na=False)]
                
                if not dish_data.empty:
                    dish_id = dish_data.iloc[0]['dish_id']
                    dish_name_full = dish_data.iloc[0]['dish_name']
                    
                    # ดึงส่วนผสมทั้งหมด
                    ingredients_used = recipe_df[recipe_df['dish_id'] == dish_id]
                    
                    # สร้างรายการส่วนผสม
                    ingredients_list = []
                    
                    for _, row in ingredients_used.iterrows():
                        ingredient_id = row['ingredient_id']
                        ingredient_data = ingredients_df[ingredients_df['ingredient_id'] == ingredient_id]
                        
                        if not ingredient_data.empty:
                            ingredient_name = ingredient_data.iloc[0]['ingredient_name']
                            amount = row['amount']
                            unit = row['unit']
                            notes = row['notes'] if pd.notna(row['notes']) else ""
                            
                            ingredient_str = f"{ingredient_name} {amount} {unit}"
                            if notes:
                                ingredient_str += f" ({notes})"
                                
                            ingredients_list.append(ingredient_str)
                    
                    # สร้างคำตอบ
                    response = f"""
ส่วนผสมของ{dish_name_full}:

{chr(10).join(['- ' + item for item in ingredients_list])}

ขั้นตอนการทำ: 
เนื่องจากในฐานข้อมูลนี้ไม่มีขั้นตอนการทำโดยละเอียด แต่โดยทั่วไป{dish_name_full}มีวิธีทำคร่าวๆ ดังนี้:
- เตรียมส่วนผสมทั้งหมดให้พร้อม
- {get_cooking_method_hint(dish_data.iloc[0]['dish_type'])}
                    """
                    return response
                else:
                    return f"ขออภัย ไม่พบข้อมูลอาหารชื่อ '{dish_name}' ในฐานข้อมูล กรุณาตรวจสอบการสะกดชื่ออาหารและลองใหม่อีกครั้ง"
            except Exception as e:
                return f"เกิดข้อผิดพลาดในการวิเคราะห์ข้อมูล: {str(e)}"
        else:
            return "กรุณาระบุชื่ออาหารที่ต้องการทราบส่วนผสม เช่น 'ส่วนผสมของต้มยำกุ้ง'"
    
    # จำลองการตอบกลับสำหรับคำถามเกี่ยวกับราคา
    elif "ราคา" in question or "price" in question.lower() or "cost" in question.lower() or "งบประมาณ" in question:
        dish_name = extract_dish_name(question)
        if dish_name:
            try:
                # หา dish_id
                dish_data = dishes_df[dishes_df['dish_name'].str.contains(dish_name, case=False)]
                
                if not dish_data.empty:
                    dish_id = dish_data.iloc[0]['dish_id']
                    dish_name_full = dish_data.iloc[0]['dish_name']
                    
                    # ดึงส่วนผสมทั้งหมด
                    ingredients_used = recipe_df[recipe_df['dish_id'] == dish_id]
                    
                    # คำนวณราคาโดยประมาณ
                    total_cost = 0
                    main_ingredients = []
                    
                    for _, row in ingredients_used.iterrows():
                        ingredient_id = row['ingredient_id']
                        ingredient_data = ingredients_df[ingredients_df['ingredient_id'] == ingredient_id]
                        
                        if not ingredient_data.empty:
                            ingredient_name = ingredient_data.iloc[0]['ingredient_name']
                            price_per_unit = float(ingredient_data.iloc[0]['price_per_unit'])
                            unit_in_db = ingredient_data.iloc[0]['unit']
                            
                            # แปลงปริมาณเป็นตัวเลขถ้าเป็นไปได้
                            try:
                                amount = float(row['amount'])
                            except:
                                # กรณีไม่สามารถแปลงเป็นตัวเลขได้ กำหนดค่าโดยประมาณ
                                if row['amount'] == 'สำหรับทอด':
                                    amount = 0.05  # น้ำมันสำหรับทอด ประมาณ 50 มล. = 0.05 ลิตร
                                elif '/' in row['amount']:
                                    # กรณีเป็นเศษส่วน เช่น 1/2
                                    nums = row['amount'].split('/')
                                    amount = float(nums[0]) / float(nums[1])
                                else:
                                    amount = 0.1  # ค่าเริ่มต้น
                            
                            # คำนวณราคาตามปริมาณที่ใช้
                            recipe_unit = row['unit']
                            
                            # คำนวณสัดส่วนตามหน่วย
                            if 'กิโลกรัม' in unit_in_db and 'กรัม' in recipe_unit:
                                # แปลงกรัมเป็นกิโลกรัม
                                unit_cost = (amount / 1000) * price_per_unit
                            elif 'ขวด' in unit_in_db and 'ช้อนโต๊ะ' in recipe_unit:
                                # ประมาณว่า 1 ขวด (700ml) มี 46 ช้อนโต๊ะ (15ml)
                                unit_cost = (amount / 46) * price_per_unit
                            elif 'ขวด' in unit_in_db and 'ช้อนชา' in recipe_unit:
                                # ประมาณว่า 1 ขวด (700ml) มี 140 ช้อนชา (5ml)
                                unit_cost = (amount / 140) * price_per_unit
                            else:
                                # กรณีอื่นๆ ใช้การประมาณอย่างง่าย
                                unit_cost = (amount / 10) * price_per_unit
                                
                            total_cost += unit_cost
                            
                            # เพิ่มวัตถุดิบหลักที่มีราคาสูง
                            if unit_cost > 5:  # วัตถุดิบที่มีราคามากกว่า 5 บาท
                                main_ingredients.append(f"{ingredient_name}: {round(unit_cost)} บาท")
                    
                    # ปรับราคาตามขนาดเสิร์ฟ 1-4 คน
                    persons = 4
                    if "สำหรับ" in question and re.search(r'(\d+)\s*คน', question):
                        match = re.search(r'(\d+)\s*คน', question)
                        persons = int(match.group(1))
                    
                    adjusted_cost = total_cost
                    if persons > 1:
                        # ปรับราคาตามจำนวนคน แต่ไม่เป็นเชิงเส้นตรง (economy of scale)
                        adjusted_cost = total_cost * (1 + (persons - 1) * 0.7) / persons
                    
                    # สร้างคำตอบ
                    response = f"""
ราคาวัตถุดิบสำหรับการทำ{dish_name_full} สำหรับ {persons} คน โดยประมาณคือ {round(adjusted_cost * persons)} บาท

วัตถุดิบหลักที่มีราคาสูง:
{chr(10).join(['- ' + item for item in main_ingredients[:5]])}

หมายเหตุ: 
- ราคานี้เป็นเพียงการประมาณการจากราคาวัตถุดิบในฐานข้อมูลเท่านั้น 
- ราคาอาจแตกต่างกันตามแหล่งที่ซื้อและฤดูกาล
- ไม่รวมค่าเครื่องปรุงพื้นฐานที่บ้านอาจมีอยู่แล้ว เช่น เกลือ น้ำตาล น้ำปลา
                    """
                    return response
                else:
                    return f"ขออภัย ไม่พบข้อมูลอาหารชื่อ '{dish_name}' ในฐานข้อมูล กรุณาตรวจสอบการสะกดชื่ออาหารและลองใหม่อีกครั้ง"
            except Exception as e:
                return f"เกิดข้อผิดพลาดในการวิเคราะห์ข้อมูล: {str(e)}"
        else:
            return "กรุณาระบุชื่ออาหารที่ต้องการทราบราคา เช่น 'ราคาของต้มยำกุ้ง'"
    
    # คำถามทั่วไปเกี่ยวกับอาหารไทย
    else:
        return f"""
ขอบคุณสำหรับคำถามเกี่ยวกับ "{question}"

ฐานข้อมูลของเราสามารถตอบคำถามเกี่ยวกับ:
1. แคลอรี่ของอาหารไทย (เช่น "แคลอรี่ของต้มยำกุ้ง")
2. ส่วนผสมของอาหารไทย (เช่น "ส่วนผสมของแกงเขียวหวาน")
3. ราคาโดยประมาณในการทำอาหารไทย (เช่น "ราคาในการทำผัดไทยสำหรับ 4 คน")

กรุณาถามคำถามใหม่โดยระบุหัวข้อและชื่ออาหารที่ต้องการทราบข้อมูล
        """

# Helper function to extract dish name from question
def extract_dish_name(question):
    # แก้ไขการดึงชื่ออาหารจากคำถาม - เพิ่มรูปแบบมากขึ้น
    original_question = question
    
    # แปลงคำถามให้เป็นตัวพิมพ์เล็กและลบเครื่องหมายคำถาม
    question = question.lower().replace('?', '').replace('ๆ', '').strip()
    
    # กรณีที่ 1: คำถามเกี่ยวกับแคลอรี่
    if "แคลอรี่ของ" in question:
        return question.split("แคลอรี่ของ")[1].strip()
    
    # กรณีที่ 2: คำถามเกี่ยวกับส่วนผสม
    if "ส่วนผสมของ" in question:
        parts = question.split("ส่วนผสมของ")[1].strip()
        # ตัดคำว่า "มีอะไรบ้าง" ออก ถ้ามี
        if "มีอะไรบ้าง" in parts:
            parts = parts.split("มีอะไรบ้าง")[0].strip()
        return parts
    
    # กรณีที่ 3: คำถามมีคำว่า "ส่วนผสม" และชื่ออาหาร
    if "ส่วนผสม" in question and "มีอะไรบ้าง" in question:
        # ลองตัดส่วนหน้า "ส่วนผสม" และหลัง "มีอะไรบ้าง" ออก
        parts = question.split("ส่วนผสม")[1].strip()
        if "มีอะไรบ้าง" in parts:
            parts = parts.split("มีอะไรบ้าง")[0].strip()
        # ถ้ามีคำว่า "ของ" ให้ดึงข้อความหลัง "ของ"
        if "ของ" in parts:
            return parts.split("ของ")[1].strip()
        return parts
    
    # กรณีที่ 4: คำถามมีคำว่า "แคลอรี่" และชื่ออาหาร
    if "แคลอรี่" in question:
        # ตัดคำว่า "แคลอรี่" ออก และลองหาชื่ออาหาร
        text = question.replace("แคลอรี่", "").strip()
        # ถ้ามีคำว่า "ของ" ให้ดึงข้อความหลัง "ของ"
        if "ของ" in text:
            return text.split("ของ")[1].strip()
    
    # กรณีที่ 5: คำถามเกี่ยวกับราคา
    if "ราคาของ" in question:
        return question.split("ราคาของ")[1].strip()
    
    if "ราคา" in question and "เท่าไหร่" in question:
        text = question.replace("ราคา", "").replace("เท่าไหร่", "").strip()
        if "ของ" in text:
            return text.split("ของ")[1].strip()
    
    # ใช้รูปแบบเดิมเป็น fallback
    patterns = [
        r'(?:ของ|about|of|for|อาหาร|ชื่อ|เมนู)\s+([^\?\.]+?)(?:\s+and|\s*$|\s+สำหรับ|\s+ราคา|\s+แคลอรี่|\s+มีอะไร)',
        r'(?:ทำ)([^\?\.]+?)(?:\s+and|\s*$|\s+สำหรับ|\s+ยังไง|\s+อย่างไร)',
        r'([^\?\.]+?)(?:\s+มี|\s+ประกอบด้วย|\s+ทำยังไง|\s+ราคา|\s+แคลอรี่)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question)
        if match:
            return match.group(1).strip()
            
    # กรณีพิเศษ: คำถามสั้นๆ ที่มีชื่ออาหารโดยตรง (ไม่มีคำว่า "ของ", "แคลอรี่" ฯลฯ)
    # เช่น "ต้มยำกุ้ง" โดยตรง
    if len(question.split()) <= 3:  # คำถามสั้นๆ ไม่เกิน 3 คำ
        return question.strip()
    
    # แสดงคำถามที่ไม่สามารถดึงชื่ออาหารได้ เพื่อการดีบัก
    print(f"DEBUG - ไม่สามารถดึงชื่ออาหารจากคำถาม: {original_question}")
    
    # ตรวจสอบในฐานข้อมูลว่ามีอาหารที่ชื่อสอดคล้องกับคำในคำถามหรือไม่
    return None

# Helper function to provide cooking method hint based on dish type
def get_cooking_method_hint(dish_type):
    cooking_hints = {
        'ต้ม': 'ต้มน้ำให้เดือด แล้วใส่วัตถุดิบลงไป ปรุงรสตามชอบ',
        'แกง': 'ผัดเครื่องแกงให้หอม เติมกะทิหรือน้ำ ใส่เนื้อสัตว์และผัก ปรุงรสตามชอบ',
        'ผัด': 'ตั้งกระทะให้ร้อน ใส่น้ำมัน แล้วผัดวัตถุดิบทั้งหมดให้สุก ปรุงรสตามชอบ',
        'ทอด': 'ตั้งกระทะน้ำมันให้ร้อน ทอดวัตถุดิบให้สุกกรอบ',
        'ยำ': 'เตรียมวัตถุดิบทั้งหมดให้พร้อม คลุกเคล้ากับน้ำยำรสเปรี้ยวหวานเผ็ด',
        'นึ่ง': 'เตรียมหม้อนึ่ง ใส่วัตถุดิบลงไปนึ่งจนสุก',
        'ตุ๋น': 'ใส่วัตถุดิบทั้งหมดลงในหม้อ แล้วตุ๋นไฟอ่อนเป็นเวลานาน',
        'ปิ้ง/ย่าง': 'หมักวัตถุดิบให้เข้าเครื่อง แล้วนำไปปิ้งหรือย่างให้สุก',
        'น้ำพริก': 'โขลกเครื่องปรุงทั้งหมดให้ละเอียด ปรุงรสตามชอบ'
    }
    
    return cooking_hints.get(dish_type, 'เตรียมและปรุงอาหารตามขั้นตอนมาตรฐานของอาหารประเภทนี้')

def generate_gemini_prompt(question, dishes_df, ingredients_df, recipe_df):
    # ฟังก์ชันนี้จะถูกเรียกใช้ในเบื้องหลัง แต่ผู้ใช้จะไม่เห็นรายละเอียดของโปรมต์
    prompt = """
You are a Thai food expert with access to a database of Thai dishes, ingredients and recipes. 
Answer the following question based on the data provided below.

QUESTION: {question}

DATABASE STRUCTURE:
1. Thai Dishes:
{dishes_structure}

2. Ingredients:
{ingredients_structure}

3. Recipe Ingredients:
{recipe_structure}

DATABASE CONTENT:
1. Thai Dishes (First 5 rows):
{dishes_sample}

2. Ingredients (First 5 rows):
{ingredients_sample}

3. Recipe Ingredients (First 10 rows):
{recipe_sample}

Provide a thorough answer based on the data. Do not include any code in your response.
If you need to calculate something, perform the calculation yourself and provide the result.
If the information is not in the database, politely say so.
"""
    
    # Fill in the template
    dishes_structure = "Not available" if dishes_df is None else dishes_df.dtypes.to_string()
    ingredients_structure = "Not available" if ingredients_df is None else ingredients_df.dtypes.to_string()
    recipe_structure = "Not available" if recipe_df is None else recipe_df.dtypes.to_string()
    
    dishes_sample = "Not available" if dishes_df is None else dishes_df.head(5).to_string()
    ingredients_sample = "Not available" if ingredients_df is None else ingredients_df.head(5).to_string()
    recipe_sample = "Not available" if recipe_df is None else recipe_df.head(10).to_string()
    
    formatted_prompt = prompt.format(
        question=question,
        dishes_structure=dishes_structure,
        ingredients_structure=ingredients_structure,
        recipe_structure=recipe_structure,
        dishes_sample=dishes_sample,
        ingredients_sample=ingredients_sample,
        recipe_sample=recipe_sample
    )
    
    # เพิ่มคำแนะนำเฉพาะสำหรับประเภทคำถาม
    if "calories" in question.lower() or "แคลอรี" in question:
        # Extract dish name from question
        dish_name_match = re.search(r'(?:of|for|about|ของ)\s+(.+?)(?:\s+and|\s*$)', question)
        if dish_name_match:
            dish_name = dish_name_match.group(1).strip()
            
            analysis_guide = f"""
ANALYSIS GUIDE:
To calculate the calories of {dish_name}, you should:
1. Find the dish_id for "{dish_name}" in the thai_dishes dataframe
2. Use that dish_id to find all ingredients in recipe_ingredients dataframe
3. For each ingredient, look up its calories_per_100g in the ingredients dataframe
4. Calculate total calories based on the amount of each ingredient used
5. Convert units appropriately (e.g., spoons to grams)
6. Present the total calories and breakdown by main ingredients
"""
            formatted_prompt += "\n\n" + analysis_guide
    
    return formatted_prompt

# Main title
st.title("🍜 Thai Food Chatbot")

# Sidebar for file upload
with st.sidebar:
    st.header("อัปโหลดไฟล์ฐานข้อมูล")
    uploaded_files = st.file_uploader("อัปโหลดไฟล์ CSV", type="csv", accept_multiple_files=True)
    
    if uploaded_files:
        for file in uploaded_files:
            try:
                # ลองอ่านไฟล์ด้วยตัวเลือกที่ยืดหยุ่นมากขึ้น
                df = pd.read_csv(
                    file,
                    encoding='utf-8',  # ระบุการเข้ารหัสเป็น UTF-8
                    on_bad_lines='skip',  # ข้ามบรรทัดที่มีปัญหา
                    low_memory=False,  # ป้องกันปัญหา low memory
                    dtype=str  # อ่านทุกคอลัมน์เป็น string ก่อน
                )
                
                # แปลงประเภทข้อมูลหลังจากโหลดไฟล์แล้ว
                for col in df.columns:
                    try:
                        # ลองแปลงเป็นตัวเลข ถ้าแปลงไม่ได้ก็ปล่อยเป็น string
                        df[col] = pd.to_numeric(df[col], errors='ignore')
                    except:
                        pass
                
                if is_data_dict(file.name):
                    st.session_state.data_dicts[file.name] = df
                    st.success(f"โหลด Data Dictionary สำเร็จ: {file.name}")
                else:
                    st.session_state.dataframes[file.name] = df
                    st.success(f"โหลดฐานข้อมูลสำเร็จ: {file.name}")
                    
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการโหลดไฟล์ {file.name}: {str(e)}")
                st.info("กำลังลองวิธีการโหลดไฟล์แบบอื่น...")
                
                try:
                    # ลองอ่านเป็นไฟล์ธรรมดาและแปลงเป็น CSV ด้วยตนเอง
                    stringio = StringIO(file.getvalue().decode("utf-8"))
                    lines = stringio.read().splitlines()
                    header = lines[0].split(",")
                    
                    data = []
                    for line in lines[1:]:
                        if line.strip():  # ข้ามบรรทัดว่าง
                            values = line.split(",")
                            if len(values) == len(header):
                                data.append(values)
                    
                    df = pd.DataFrame(data, columns=header)
                    
                    if is_data_dict(file.name):
                        st.session_state.data_dicts[file.name] = df
                        st.success(f"โหลด Data Dictionary สำเร็จ (วิธีที่ 2): {file.name}")
                    else:
                        st.session_state.dataframes[file.name] = df
                        st.success(f"โหลดฐานข้อมูลสำเร็จ (วิธีที่ 2): {file.name}")
                        
                except Exception as e2:
                    st.error(f"ไม่สามารถโหลดไฟล์ {file.name} ได้: {str(e2)}")
                except Exception as e2:
                    st.error(f"ไม่สามารถโหลดไฟล์ {file.name} ได้: {str(e2)}")
        
        st.session_state.file_uploaded = True

# Main content - Chat interface
if st.session_state.file_uploaded:
    # Get DataFrames
    dishes_df = None
    ingredients_df = None
    recipe_df = None
    
    for filename, df in st.session_state.dataframes.items():
        if isinstance(filename, str) and 'thai_dishes' in filename.lower():
            dishes_df = df
        elif isinstance(filename, str) and 'ingredients' in filename.lower() and 'recipe' not in filename.lower():
            ingredients_df = df
        elif isinstance(filename, str) and 'recipe' in filename.lower():
            recipe_df = df
    
    # เพิ่มการตรวจสอบว่าได้ข้อมูลครบหรือไม่
    if dishes_df is None or ingredients_df is None or recipe_df is None:
        st.error("ไม่พบข้อมูลที่จำเป็นครบถ้วน กรุณาตรวจสอบไฟล์ที่อัปโหลด")
        st.write("สถานะข้อมูล:")
        st.write(f"- ข้อมูลอาหารไทย (thai_dishes): {'พบแล้ว' if dishes_df is not None else 'ไม่พบ'}")
        st.write(f"- ข้อมูลวัตถุดิบ (ingredients): {'พบแล้ว' if ingredients_df is not None else 'ไม่พบ'}")
        st.write(f"- ข้อมูลส่วนผสม (recipe_ingredients): {'พบแล้ว' if recipe_df is not None else 'ไม่พบ'}")
        
        # ถ้าไม่ครบให้แสดงรายชื่อไฟล์ที่โหลดแล้ว
        st.write("ไฟล์ที่โหลดแล้ว:")
        for filename in st.session_state.dataframes.keys():
            st.write(f"- {filename}")
    
    # Display chat interface
    st.header("สนทนากับแชทบอทอาหารไทย")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for i, (q, a) in enumerate(st.session_state.chat_history):
            st.markdown(f"**คุณ**: {q}")
            st.markdown(f"**แชทบอท**: {a}")
            if i < len(st.session_state.chat_history) - 1:
                st.markdown("---")
    
    # Input for new question
    with st.form(key="question_form"):
        question = st.text_input("ถามคำถามเกี่ยวกับอาหารไทย:", placeholder="เช่น แคลอรี่ของต้มยำกุ้ง, ส่วนผสมของแกงเขียวหวาน, ราคาในการทำผัดไทยสำหรับ 4 คน")
        submit_button = st.form_submit_button("ถามคำถาม")
        
        if submit_button and question:
            # Get response
            if dishes_df is not None and ingredients_df is not None and recipe_df is not None:
                response = get_response_for_question(question, dishes_df, ingredients_df, recipe_df)
            else:
                response = "ขออภัย ยังไม่มีข้อมูลอาหารไทยในระบบ กรุณาอัปโหลดไฟล์ CSV ทั้งหมดก่อน"
            
            # Add to chat history
            st.session_state.chat_history.append((question, response))
            
            # Rerun to update chat display
            st.rerun()
    
    # Add option to clear chat history
    if st.button("ล้างประวัติการสนทนา"):
        st.session_state.chat_history = []
        st.rerun()

    # Add export chat history
    if st.download_button(
        label="ดาวน์โหลดประวัติการสนทนา",
        data="\n\n".join([f"คำถาม: {q}\n\nคำตอบ: {a}" for q, a in st.session_state.chat_history]),
        file_name="thai_food_chat_history.txt",
        mime="text/plain"
    ):
        st.success("ดาวน์โหลดประวัติการสนทนาเรียบร้อยแล้ว")
        
else:
    st.info("กรุณาอัปโหลดไฟล์ CSV ทั้งหมดก่อนเริ่มสนทนากับแชทบอท")
    st.write("ควรอัปโหลดไฟล์ต่อไปนี้:")
    st.write("1. thai_dishes.csv - รายการอาหารไทย")
    st.write("2. ingredients.csv - วัตถุดิบ")
    st.write("3. recipe_ingredients.csv - ความสัมพันธ์ระหว่างอาหารและวัตถุดิบ")
    st.write("4. thai_dishes_data_dict.csv - คำอธิบายโครงสร้างข้อมูลของรายการอาหาร (ไม่จำเป็นต้องมี)")
    st.write("5. ingredients_data_dict.csv - คำอธิบายโครงสร้างข้อมูลของวัตถุดิบ (ไม่จำเป็นต้องมี)")
    st.write("6. recipe_ingredients_data_dict.csv - คำอธิบายโครงสร้างข้อมูลความสัมพันธ์ (ไม่จำเป็นต้องมี)")
    
    st.write("## วิธีใช้งาน")
    st.write("1. อัปโหลดไฟล์ CSV ทั้งหมดผ่านช่องทางด้านซ้าย")
    st.write("2. ระบบจะแยกแยะไฟล์อัตโนมัติระหว่างฐานข้อมูลและ Data Dictionary")
    st.write("3. พิมพ์คำถามเกี่ยวกับอาหารไทยในช่องข้อความและกดปุ่ม 'ถามคำถาม'")
    st.write("4. แชทบอทจะวิเคราะห์ฐานข้อมูลและตอบคำถามของคุณ")
    
    # Add example questions
    st.write("## ตัวอย่างคำถาม")
    st.write("- แคลอรี่ของต้มยำกุ้งเท่าไหร่?")
    st.write("- ส่วนผสมของแกงเขียวหวานไก่มีอะไรบ้าง?")
    st.write("- ราคาในการทำผัดไทยสำหรับ 4 คนประมาณเท่าไหร่?")
    st.write("- อยากทำต้มข่าไก่ต้องใช้วัตถุดิบอะไรบ้าง?")
    st.write("- แกงมัสมั่นใช้งบประมาณเท่าไหร่?")

# Run the app
if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.info("แชทบอทนี้ใช้ฐานข้อมูลอาหารไทยที่มีข้อมูลอาหาร 50 รายการ, วัตถุดิบ 70 รายการ และสูตรอาหารที่เกี่ยวข้อง")
    
    # แสดงสถานะการโหลดไฟล์
    if st.session_state.file_uploaded:
        st.sidebar.success(f"โหลดไฟล์ทั้งหมด {len(st.session_state.dataframes) + len(st.session_state.data_dicts)} ไฟล์")
        st.sidebar.markdown("**ไฟล์ฐานข้อมูล:**")
        for filename in st.session_state.dataframes.keys():
            st.sidebar.markdown(f"- {filename}")
        
        if st.session_state.data_dicts:
            st.sidebar.markdown("**ไฟล์ Data Dictionary:**")
            for filename in st.session_state.data_dicts.keys():
                st.sidebar.markdown(f"- {filename}")
    else:
        st.sidebar.warning("ยังไม่ได้โหลดไฟล์ฐานข้อมูล")
