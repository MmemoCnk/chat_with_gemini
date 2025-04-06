import streamlit as st
import pandas as pd
import os
import json
import re
from io import StringIO
import google.generativeai as genai
import glob

st.set_page_config(
    page_title="Thai Food Chatbot with Gemini",
    page_icon="🍜",
    layout="wide"
)

# Hard-coded Gemini API key - ให้ใส่ API key ของคุณที่นี่
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"  # แทนที่ด้วย API key จริง

# Initialize session state for storing dataframes
if 'dataframes' not in st.session_state:
    st.session_state.dataframes = {}
if 'data_dicts' not in st.session_state:
    st.session_state.data_dicts = {}
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'api_key_set' not in st.session_state:
    st.session_state.api_key_set = False

# Function to initialize Gemini API
def initialize_gemini_api(api_key):
    try:
        # กำหนดค่า API key
        genai.configure(api_key=api_key)
        # สร้าง model
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        return model, True
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อกับ Gemini API ได้: {str(e)}")
        return None, False

# Function to determine if file is a data dictionary
def is_data_dict(filename):
    return 'data_dict' in filename

# Function to load CSV files from directories
def load_csv_from_directories():
    loaded_files = 0
    
    # ตรวจสอบและโหลดไฟล์จากโฟลเดอร์ data_dict
    if os.path.exists("csv/data_dict"):
        csv_files = glob.glob("csv/data_dict/*.csv")
        for file_path in csv_files:
            try:
                filename = os.path.basename(file_path)
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip', low_memory=False)
                st.session_state.data_dicts[filename] = df
                loaded_files += 1
                st.sidebar.success(f"โหลด Data Dictionary สำเร็จ: {filename}")
            except Exception as e:
                st.sidebar.error(f"ไม่สามารถโหลดไฟล์ {filename} ได้: {str(e)}")
    
    # ตรวจสอบและโหลดไฟล์จากโฟลเดอร์ database
    if os.path.exists("csv/database"):
        csv_files = glob.glob("csv/database/*.csv")
        for file_path in csv_files:
            try:
                filename = os.path.basename(file_path)
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip', low_memory=False)
                
                # แปลงประเภทข้อมูลหลังจากโหลดไฟล์แล้ว
                for col in df.columns:
                    try:
                        # ลองแปลงเป็นตัวเลข ถ้าแปลงไม่ได้ก็ปล่อยเป็น string
                        df[col] = pd.to_numeric(df[col], errors='ignore')
                    except:
                        pass
                        
                st.session_state.dataframes[filename] = df
                loaded_files += 1
                st.sidebar.success(f"โหลดฐานข้อมูลสำเร็จ: {filename}")
            except Exception as e:
                st.sidebar.error(f"ไม่สามารถโหลดไฟล์ {filename} ได้: {str(e)}")
    
    return loaded_files > 0

# สร้างข้อมูลทดสอบ (เพิ่มเติม)
def create_test_data():
    # สร้างข้อมูลทดสอบสำหรับอาหารไทย
    dishes_data = {
        'dish_id': [1, 2, 3],
        'dish_name': ['ต้มยำกุ้ง', 'แกงเขียวหวานไก่', 'ผัดไทย'],
        'dish_type': ['ต้ม', 'แกง', 'ผัด'],
        'description': [
            'ต้มยำกุ้งเป็นอาหารไทยที่มีรสเปรี้ยวเผ็ด หอมสมุนไพร นิยมใส่กุ้งเป็นหลัก',
            'แกงเขียวหวานไก่เป็นแกงกะทิรสเผ็ดหวาน มีสีเขียวจากพริกแกงเขียวหวาน นิยมใส่ไก่และผักต่างๆ',
            'ผัดไทยเป็นอาหารผัดที่มีเส้นเป็นหลัก ปรุงรสเปรี้ยวหวาน มีไข่ ถั่วงอก และกุ้งหรือหมู'
        ]
    }
    dishes_df = pd.DataFrame(dishes_data)
    
    # สร้างข้อมูลทดสอบสำหรับวัตถุดิบ
    ingredients_data = {
        'ingredient_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'ingredient_name': ['กุ้ง', 'น้ำพริกเผา', 'น้ำมะนาว', 'พริกขี้หนู', 'ข่า', 
                            'ไก่', 'กะทิ', 'พริกแกง', 'ใบมะกรูด', 'เส้นผัดไทย'],
        'calories_per_100g': [100, 200, 5, 40, 60, 120, 230, 180, 30, 350],
        'price_per_unit': [300, 80, 20, 100, 50, 80, 60, 90, 20, 40],
        'unit': ['กิโลกรัม', 'ขวด', 'ขวด', 'กิโลกรัม', 'กิโลกรัม', 
                'กิโลกรัม', 'กระป๋อง', 'ขวด', 'กิโลกรัม', 'กิโลกรัม']
    }
    ingredients_df = pd.DataFrame(ingredients_data)
    
    # สร้างข้อมูลทดสอบสำหรับส่วนผสมในสูตรอาหาร
    recipe_data = {
        'dish_id': [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3],
        'ingredient_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 4, 10, 1, 3, 4, 2, 7],
        'amount': [300, 2, 3, 5, 50, 500, 400, 3, 5, 3, 200, 100, 2, 2, 2, 100],
        'unit': ['กรัม', 'ช้อนโต๊ะ', 'ช้อนโต๊ะ', 'เม็ด', 'กรัม', 
                'กรัม', 'กรัม', 'ช้อนโต๊ะ', 'ใบ', 'เม็ด', 
                'กรัม', 'กรัม', 'ช้อนโต๊ะ', 'เม็ด', 'ช้อนโต๊ะ', 'กรัม'],
        'notes': ['สด', '', '', 'สด', 'หั่นแว่น', 'หั่นชิ้น', '', '', 'ฉีก', '', 'แช่น้ำ', 'ปอกเปลือก', '', 'บุบ', '', '']
    }
    recipe_df = pd.DataFrame(recipe_data)
    
    # สร้างข้อมูลทดสอบสำหรับวิธีทำอาหาร
    cooking_steps_data = {
        'dish_id': [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3],
        'step_number': [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 5],
        'instruction': [
            'ตั้งน้ำให้เดือด', 
            'ใส่ข่า ตะไคร้ ใบมะกรูด', 
            'ใส่กุ้งลงไปต้มจนสุก', 
            'ปรุงรสด้วยน้ำปลา น้ำมะนาว น้ำพริกเผา',
            'ผัดพริกแกงกับกะทิจนหอม',
            'ใส่ไก่ผัดจนเกือบสุก',
            'เติมกะทิ ปรุงรสด้วยน้ำปลา น้ำตาล',
            'ใส่ผัก ใบมะกรูด เคี่ยวจนสุก',
            'แช่เส้นในน้ำอุ่นจนนิ่ม',
            'ผัดกระเทียมกับน้ำมัน ใส่กุ้งและเส้น',
            'ตอกไข่ลงไปผัดให้สุก',
            'ปรุงรสด้วยน้ำปลา น้ำตาล น้ำมะนาว',
            'ใส่ถั่วงอก ใบกุยช่าย ผัดให้เข้ากัน'
        ]
    }
    cooking_steps_df = pd.DataFrame(cooking_steps_data)
    
    return dishes_df, ingredients_df, recipe_df, cooking_steps_df

# Function to generate prompt for Gemini
def generate_gemini_prompt(question, dataframes):
    # Extract all dataframes
    dishes_df = dataframes.get('dishes_df')
    ingredients_df = dataframes.get('ingredients_df')
    recipe_df = dataframes.get('recipe_df')
    cooking_steps_df = dataframes.get('cooking_steps_df', None)
    
    prompt = """
คุณเป็นผู้เชี่ยวชาญด้านอาหารไทยที่มีข้อมูลเกี่ยวกับอาหารไทย วัตถุดิบ และสูตรอาหาร
กรุณาตอบคำถามต่อไปนี้โดยใช้ข้อมูลที่ให้มา:

คำถาม: {question}

ข้อมูลในฐานข้อมูล:

1. ข้อมูลอาหารไทย (dishes_df):
{dishes_data}

2. ข้อมูลวัตถุดิบ (ingredients_df):
{ingredients_data}

3. ข้อมูลส่วนผสมในสูตรอาหาร (recipe_df):
{recipe_data}
"""

    # เพิ่มข้อมูลวิธีทำถ้ามี
    if cooking_steps_df is not None:
        prompt += """
4. ข้อมูลวิธีทำอาหาร (cooking_steps_df):
{cooking_steps_data}
"""
        prompt = prompt.format(
            question=question,
            dishes_data=dishes_df.to_string() if dishes_df is not None else "ไม่มีข้อมูล",
            ingredients_data=ingredients_df.to_string() if ingredients_df is not None else "ไม่มีข้อมูล",
            recipe_data=recipe_df.to_string() if recipe_df is not None else "ไม่มีข้อมูล",
            cooking_steps_data=cooking_steps_df.to_string() if cooking_steps_df is not None else "ไม่มีข้อมูล"
        )
    else:
        prompt = prompt.format(
            question=question,
            dishes_data=dishes_df.to_string() if dishes_df is not None else "ไม่มีข้อมูล",
            ingredients_data=ingredients_df.to_string() if ingredients_df is not None else "ไม่มีข้อมูล",
            recipe_data=recipe_df.to_string() if recipe_df is not None else "ไม่มีข้อมูล"
        )
    
    prompt += """
คำแนะนำเพิ่มเติม:
1. ตอบคำถามให้ครบถ้วนตามข้อมูลที่มีในฐานข้อมูล
2. หากมีการคำนวณ (เช่น แคลอรี่, ราคา) ให้อธิบายวิธีคำนวณด้วย
3. หากข้อมูลในฐานข้อมูลไม่เพียงพอ ให้บอกอย่างสุภาพว่าไม่มีข้อมูลเพียงพอ
4. ตอบในรูปแบบที่อ่านง่าย มีการจัดย่อหน้าและหัวข้ออย่างเหมาะสม
5. ตอบเป็นภาษาไทยเสมอ
"""
    
    return prompt

# Function to get response from Gemini
def get_gemini_response(model, question, dataframes):
    try:
        # สร้าง prompt
        prompt = generate_gemini_prompt(question, dataframes)
        
        # ส่งไปยัง Gemini API
        response = model.generate_content(prompt)
        
        # แปลงผลลัพธ์เป็นข้อความ
        return response.text
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการเรียกใช้ Gemini API: {str(e)}\n\nกรุณาตรวจสอบ API Key และการเชื่อมต่ออินเทอร์เน็ต"

# Main title
st.title("🍜 Thai Food Chatbot with Gemini")

# Sidebar for file upload and options
with st.sidebar:
    st.header("สถานะ Gemini API")
    
    # ใช้ Hard-coded API Key แทนการให้ผู้ใช้กรอก
    if GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        # Initialize Gemini API with hard-coded key
        gemini_model, success = initialize_gemini_api(GEMINI_API_KEY)
        if success:
            st.session_state.gemini_model = gemini_model
            st.session_state.api_key_set = True
            st.success("เชื่อมต่อกับ Gemini API สำเร็จ")
        else:
            st.session_state.api_key_set = False
            st.error("ไม่สามารถเชื่อมต่อกับ Gemini API ได้ กรุณาตรวจสอบ API Key")
    else:
        st.warning("ยังไม่ได้กำหนด Gemini API Key ในโค้ด กรุณาแก้ไขตัวแปร GEMINI_API_KEY")
    
    st.header("ข้อมูลฐานข้อมูล")
    
    # ตรวจสอบว่ามีไฟล์ใน folder csv/data_dict และ csv/database หรือไม่
    has_csv_folders = (os.path.exists("csv/data_dict") or os.path.exists("csv/database"))
    
    # ถ้ามี folder csv ให้โหลดไฟล์อัตโนมัติ
    if has_csv_folders:
        if st.button("โหลดไฟล์จากโฟลเดอร์ csv อัตโนมัติ"):
            loaded = load_csv_from_directories()
            if loaded:
                st.session_state.file_uploaded = True
            else:
                st.error("ไม่พบไฟล์ CSV ใน csv/data_dict หรือ csv/database")
    else:
        st.info("ไม่พบโฟลเดอร์ csv/data_dict หรือ csv/database กรุณาสร้างโฟลเดอร์และเพิ่มไฟล์ CSV หรือใช้การอัปโหลดไฟล์แทน")
    
    # คงฟังก์ชันอัปโหลดไฟล์ไว้เป็นทางเลือก
    st.header("อัปโหลดไฟล์ฐานข้อมูล")
    uploaded_files = st.file_uploader("อัปโหลดไฟล์ CSV", type="csv", accept_multiple_files=True)
    
    # เพิ่มปุ่มโหลดข้อมูลตัวอย่าง
    use_sample_data = st.checkbox("ใช้ข้อมูลตัวอย่าง (สำหรับทดสอบ)")
    
    if use_sample_data:
        # สร้างข้อมูลตัวอย่างและเก็บไว้ใน session_state
        dishes_df, ingredients_df, recipe_df, cooking_steps_df = create_test_data()
        st.session_state.dataframes = {
            'thai_dishes.csv': dishes_df,
            'ingredients.csv': ingredients_df,
            'recipe_ingredients.csv': recipe_df,
            'cooking_steps.csv': cooking_steps_df
        }
        st.session_state.file_uploaded = True
        st.success("โหลดข้อมูลตัวอย่างสำเร็จ")
    
    elif uploaded_files:
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
        
        # ตรวจสอบว่ามีไฟล์ที่จำเป็นครบหรือไม่
        required_files = ['thai_dishes', 'ingredients', 'recipe_ingredients']
        has_all_required = True
        
        for req in required_files:
            found = False
            for filename in st.session_state.dataframes.keys():
                if req in filename:
                    found = True
                    break
            if not found:
                has_all_required = False
                st.warning(f"ยังไม่พบไฟล์ {req}.csv กรุณาอัปโหลดไฟล์นี้")
        
        if has_all_required:
            st.session_state.file_uploaded = True
        else:
            st.session_state.file_uploaded = False

# Main content - Chat interface
if st.session_state.file_uploaded:
    # Get DataFrames
    dishes_df = None
    ingredients_df = None
    recipe_df = None
    cooking_steps_df = None
    
    for filename, df in st.session_state.dataframes.items():
        if isinstance(filename, str) and 'thai_dishes' in filename.lower():
            dishes_df = df
        elif isinstance(filename, str) and 'ingredients' in filename.lower() and 'recipe' not in filename.lower():
            ingredients_df = df
        elif isinstance(filename, str) and 'recipe' in filename.lower():
            recipe_df = df
        elif isinstance(filename, str) and ('cooking' in filename.lower() or 'steps' in filename.lower()):
            cooking_steps_df = df
    
    # เพิ่มการตรวจสอบว่าได้ข้อมูลครบหรือไม่
    if dishes_df is None or ingredients_df is None or recipe_df is None:
        st.error("ไม่พบข้อมูลที่จำเป็นครบถ้วน กรุณาตรวจสอบไฟล์ที่อัปโหลด")
        st.write("สถานะข้อมูล:")
        st.write(f"- ข้อมูลอาหารไทย (thai_dishes): {'พบแล้ว' if dishes_df is not None else 'ไม่พบ'}")
        st.write(f"- ข้อมูลวัตถุดิบ (ingredients): {'พบแล้ว' if ingredients_df is not None else 'ไม่พบ'}")
        st.write(f"- ข้อมูลส่วนผสม (recipe_ingredients): {'พบแล้ว' if recipe_df is not None else 'ไม่พบ'}")
        st.write(f"- ข้อมูลวิธีทำ (cooking_steps): {'พบแล้ว (ไม่จำเป็นต้องมี)' if cooking_steps_df is not None else 'ไม่พบ (ไม่จำเป็นต้องมี)'}")
        
        # ถ้าไม่ครบให้แสดงรายชื่อไฟล์ที่โหลดแล้ว
        st.write("ไฟล์ที่โหลดแล้ว:")
        for filename in st.session_state.dataframes.keys():
            st.write(f"- {filename}")
    else:
        # ตรวจสอบว่ามี Gemini API key หรือไม่
        if not st.session_state.api_key_set:
            st.warning("ยังไม่ได้กำหนด Gemini API Key ที่ถูกต้อง กรุณาตรวจสอบค่า GEMINI_API_KEY ในโค้ด")
        
        # รวบรวม dataframes ที่มีทั้งหมด
        all_dataframes = {
            'dishes_df': dishes_df,
            'ingredients_df': ingredients_df,
            'recipe_df': recipe_df
        }
        
        if cooking_steps_df is not None:
            all_dataframes['cooking_steps_df'] = cooking_steps_df
        
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
            question = st.text_input("ถามคำถามเกี่ยวกับอาหารไทย:", placeholder="เช่น วิธีทำต้มยำกุ้ง, แคลอรี่ของผัดไทย, ส่วนผสมของแกงเขียวหวาน, ราคาในการทำผัดไทยสำหรับ 4 คน")
            submit_button = st.form_submit_button("ถามคำถาม")
            
            if submit_button and question:
                # Get response
                if st.session_state.api_key_set and 'gemini_model' in st.session_state:
                    # ใช้ Gemini API
                    response = get_gemini_response(st.session_state.gemini_model, question, all_dataframes)
                else:
                    response = "กรุณากำหนด Gemini API Key ที่ถูกต้องในโค้ด (ตัวแปร GEMINI_API_KEY) เพื่อให้ระบบสามารถตอบคำถามของคุณได้"
                
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
    st.info("กรุณาโหลดข้อมูลจากโฟลเดอร์ csv หรืออัปโหลดไฟล์ CSV หรือเลือกใช้ข้อมูลตัวอย่างก่อนเริ่มสนทนากับแชทบอท")
    
    if os.path.exists("csv/data_dict") or os.path.exists("csv/database"):
        st.write("📂 ตรวจพบโฟลเดอร์ csv/data_dict หรือ csv/database กรุณากดปุ่ม 'โหลดไฟล์จากโฟลเดอร์ csv อัตโนมัติ' ที่เมนูด้านซ้าย")
    
    st.write("ควรมีไฟล์ต่อไปนี้:")
    st.write("1. thai_dishes.csv - รายการอาหารไทย")
    st.write("2. ingredients.csv - วัตถุดิบ")
    st.write("3. recipe_ingredients.csv - ความสัมพันธ์ระหว่างอาหารและวัตถุดิบ")
    st.write("4. cooking_steps.csv - ขั้นตอนการทำอาหาร (ไม่จำเป็นต้องมี)")
    st.write("5. thai_dishes_data_dict.csv - คำอธิบายโครงสร้างข้อมูลของรายการอาหาร (ไม่จำเป็นต้องมี)")
    st.write("6. ingredients_data_dict.csv - คำอธิบายโครงสร้างข้อมูลของวัตถุดิบ (ไม่จำเป็นต้องมี)")
    st.write("7. recipe_ingredients_data_dict.csv - คำอธิบายโครงสร้างข้อมูลความสัมพันธ์ (ไม่จำเป็นต้องมี)")
    
    st.write("## วิธีใช้งาน")
    st.write("1. โหลดข้อมูลจากโฟลเดอร์ csv โดยกดปุ่ม 'โหลดไฟล์จากโฟลเดอร์ csv อัตโนมัติ' (แนะนำ)")
    st.write("2. หรือใช้การอัปโหลดไฟล์ CSV ผ่านช่องทางด้านซ้าย")
    st.write("3. หรือเลือก 'ใช้ข้อมูลตัวอย่าง' สำหรับการทดสอบ")
    st.write("4. พิมพ์คำถามเกี่ยวกับอาหารไทยในช่องข้อความและกดปุ่ม 'ถามคำถาม'")
    st.write("5. คุณสามารถถามคำถามได้ทุกรูปแบบที่เกี่ยวข้องกับข้อมูลในฐานข้อมูล")
    
    # Add example questions
    st.write("## ตัวอย่างคำถาม")
    st.write("- วิธีทำต้มยำกุ้งมีอะไรบ้าง?")
    st.write("- แคลอรี่ของผัดไทยต่อจานเท่าไหร่?")
    st.write("- ส่วนผสมของแกงเขียวหวานไก่มีอะไรบ้าง?")
    st.write("- อยากทำต้มข่าไก่ต้องใช้วัตถุดิบอะไรบ้าง?")
    st.write("- ราคาในการทำผัดไทยสำหรับ 4 คนประมาณเท่าไหร่?")
    st.write("- แกงมัสมั่นใช้งบประมาณเท่าไหร่?")
    st.write("- ผัดไทยทำยังไง?")
    st.write("- อธิบายขั้นตอนการทำต้มยำกุ้ง")
    st.write("- อาหารไทยที่มีแคลอรี่น้อยที่สุดคืออะไร?")

# Run the app
if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.info("แชทบอทนี้ใช้ Gemini API ในการตอบคำถามเกี่ยวกับอาหารไทยโดยอ้างอิงจากฐานข้อมูลที่มี สามารถตอบคำถามได้ทุกรูปแบบที่เกี่ยวข้องกับข้อมูลในฐานข้อมูล")
    
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
        st.sidebar.warning("ยังไม่ได้โหลดไฟล์ฐานข้อมูล กรุณาโหลดข้อมูลจากโฟลเดอร์ csv หรืออัปโหลดไฟล์ CSV หรือเลือกข้อมูลตัวอย่าง")
