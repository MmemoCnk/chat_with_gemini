import streamlit as st
import pandas as pd
import os
import json
import re

st.set_page_config(
    page_title="Thai Food Database",
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

# Function to determine if file is a data dictionary
def is_data_dict(filename):
    return 'data_dict' in filename

# Main title
st.title("🍜 Thai Food Database App")

# Sidebar for file upload
with st.sidebar:
    st.header("Upload Files")
    uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)
    
    if uploaded_files:
        for file in uploaded_files:
            # Check if file is a data dictionary or a database file
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
                    st.success(f"Data Dictionary loaded: {file.name}")
                else:
                    st.session_state.dataframes[file.name] = df
                    st.success(f"Database loaded: {file.name}")
                    
            except Exception as e:
                st.error(f"Error loading {file.name}: {str(e)}")
                st.info("Trying alternative loading method...")
                
                try:
                    # ลองอ่านเป็นไฟล์ธรรมดาและแปลงเป็น CSV ด้วยตนเอง
                    stringio = file.getvalue().decode("utf-8")
                    lines = stringio.split("\n")
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
                        st.success(f"Data Dictionary loaded (alternative method): {file.name}")
                    else:
                        st.session_state.dataframes[file.name] = df
                        st.success(f"Database loaded (alternative method): {file.name}")
                        
                except Exception as e2:
                    st.error(f"Both loading methods failed for {file.name}: {str(e2)}")
                    st.warning("Please check your CSV file format and try again.")
        
        st.session_state.file_uploaded = True

# Main content
if st.session_state.file_uploaded:
    st.header("Uploaded Files")
    
    # Display tabs for each type of file
    tab1, tab2 = st.tabs(["Database Files", "Data Dictionaries"])
    
    with tab1:
        st.subheader("Database Files")
        for filename, df in st.session_state.dataframes.items():
            st.write(f"**{filename}**")
            st.dataframe(df)
            st.markdown("---")
    
    with tab2:
        st.subheader("Data Dictionaries")
        for filename, df in st.session_state.data_dicts.items():
            st.write(f"**{filename}**")
            st.dataframe(df)
            st.markdown("---")
    
    # Generate Gemini Prompt Section
    st.header("Generate Gemini Prompt")
    
    question = st.text_input("Enter your question about Thai food:", "Show me the calories of ต้มยำกุ้ง")
    
    if st.button("Generate Prompt"):
        # Extract key DataFrames
        dishes_df = None
        ingredients_df = None
        recipe_df = None
        
        for filename, df in st.session_state.dataframes.items():
            if 'thai_dishes' in filename:
                dishes_df = df
            elif 'ingredients' in filename:
                ingredients_df = df
            elif 'recipe_ingredients' in filename:
                recipe_df = df
        
        # Generate prompt for Gemini
        prompt = generate_gemini_prompt(question, dishes_df, ingredients_df, recipe_df)
        
        st.subheader("Generated Prompt for Gemini")
        st.text_area("Copy this prompt to Gemini:", prompt, height=300)

else:
    st.info("Please upload CSV files using the sidebar.")
    st.write("You should upload the following files:")
    st.write("1. thai_dishes.csv - รายการอาหารไทย")
    st.write("2. ingredients.csv - วัตถุดิบ")
    st.write("3. recipe_ingredients.csv - ความสัมพันธ์ระหว่างอาหารและวัตถุดิบ")
    st.write("4. thai_dishes_data_dict.csv - คำอธิบายโครงสร้างข้อมูลของรายการอาหาร")
    st.write("5. ingredients_data_dict.csv - คำอธิบายโครงสร้างข้อมูลของวัตถุดิบ")
    st.write("6. recipe_ingredients_data_dict.csv - คำอธิบายโครงสร้างข้อมูลความสัมพันธ์")

def generate_gemini_prompt(question, dishes_df, ingredients_df, recipe_df):
    # Create prompt template for Gemini
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
    
    # Add code to analyze the specific question
    if "calories" in question.lower() and dishes_df is not None and ingredients_df is not None and recipe_df is not None:
        # Extract dish name from question
        dish_name_match = re.search(r'(?:of|for|about)\s+(.+?)(?:\s+and|\s*$)', question)
        if dish_name_match:
            dish_name = dish_name_match.group(1).strip()
            
            # Add analysis instructions
            analysis_code = f"""
To analyze the calories of {dish_name}, you should:
1. Find the dish_id for "{dish_name}" in the thai_dishes dataframe
2. Use that dish_id to find all ingredients in recipe_ingredients dataframe
3. For each ingredient, look up its calories_per_100g in the ingredients dataframe
4. Calculate total calories based on the amount of each ingredient used

Example Python code to perform this analysis:
```python
# Find dish ID
dish_id = dishes_df[dishes_df['dish_name'] == '{dish_name}']['dish_id'].values[0]

# Get all ingredients for this dish
dish_ingredients = recipe_df[recipe_df['dish_id'] == dish_id]

# Calculate total calories
total_calories = 0
for _, row in dish_ingredients.iterrows():
    ingredient_id = row['ingredient_id']
    # Convert amount to float if possible, otherwise estimate
    try:
        amount = float(row['amount'])
    except:
        if row['amount'] == 'สำหรับทอด':
            amount = 50  # Estimate for frying oil
        else:
            amount = 10  # Default small amount
    
    # Get calories for this ingredient
    calories_per_100g = ingredients_df[ingredients_df['ingredient_id'] == ingredient_id]['calories_per_100g'].values[0]
    
    # Calculate calories for this ingredient based on amount used
    ingredient_calories = (amount / 100) * calories_per_100g
    total_calories += ingredient_calories

print(f"Total estimated calories for {dish_name}: {total_calories:.2f}")
```
"""
            formatted_prompt += "\n\n" + analysis_code
    
    return formatted_prompt

# Run the app
if __name__ == "__main__":
    st.sidebar.info("เมื่ออัปโหลดไฟล์เสร็จแล้ว คุณสามารถดูข้อมูลและสร้างโปรมต์สำหรับ Gemini ได้")
    
    # แสดงคำอธิบายเพิ่มเติมเมื่อยังไม่มีการอัปโหลดไฟล์
    if not st.session_state.file_uploaded:
        st.write("## วิธีใช้งาน")
        st.write("1. อัปโหลดไฟล์ CSV ทั้ง 6 ไฟล์ผ่านช่องทางด้านซ้าย")
        st.write("2. ระบบจะแยกแยะไฟล์อัตโนมัติระหว่างฐานข้อมูลและ Data Dictionary")
        st.write("3. ดูข้อมูลในแท็บ 'Database Files' และ 'Data Dictionaries'")
        st.write("4. ใส่คำถามเกี่ยวกับอาหารไทยในช่อง 'Enter your question about Thai food'") 
        st.write("5. กดปุ่ม 'Generate Prompt' เพื่อสร้างโปรมต์สำหรับส่งให้ Gemini")
        st.write("6. คัดลอกโปรมต์ไปวางในแชทของ Gemini เพื่อรับคำตอบ")
