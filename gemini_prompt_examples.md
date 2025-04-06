# ตัวอย่างโปรมต์สำหรับ Gemini เพื่อตอบคำถามจากฐานข้อมูลอาหารไทย

เมื่อผู้ใช้ต้องการข้อมูลเกี่ยวกับอาหารไทยจากฐานข้อมูล คุณควรส่งโปรมต์ที่มีรูปแบบดังต่อไปนี้ให้กับ Gemini:

## ตัวอย่างโปรมต์ที่ 1: คำนวณแคลอรี่สำหรับอาหารไทย

```
You are a Thai food expert with access to a database of Thai dishes, ingredients and recipes. 
Answer the following question based on the data provided below.

QUESTION: Show me the calories of ต้มยำกุ้ง

DATABASE STRUCTURE:
1. Thai Dishes:
dish_id        object
dish_name      object
dish_type      object
region         object
spicy_level     int64
cooking_time_minutes   int64
difficulty_level       int64
description    object

2. Ingredients:
ingredient_id    object
ingredient_name  object
category         object
price_per_unit   float64
unit             object
source           object
shelf_life_days  int64
calories_per_100g int64

3. Recipe Ingredients:
dish_id        object
ingredient_id  object
amount         object
unit           object
notes          object

DATABASE CONTENT:
1. Thai Dishes (First 5 rows):
  dish_id       dish_name dish_type region  spicy_level  cooking_time_minutes  difficulty_level                                        description
0    D001        ต้มยำกุ้ง       ต้ม   กลาง            4                    30                 3  ต้มยำกุ้งน้ำใสรสจัด หอมสมุนไพรไทย กุ้งสด เป็นอาหารยอดนิยมของไทย
1    D002         ผัดไทย       ผัด   กลาง            2                    20                 2        ก๋วยเตี๋ยวผัดกับไข่ เต้าหู้ และถั่วงอก ปรุงรสด้วยน้ำปลา น้ำตาล มะนาว
2    D003  แกงเขียวหวานไก่      แกง   กลาง            3                    45                 3        แกงกะทิรสเผ็ดอ่อนๆ หอมเครื่องแกง มีมะเขือ และพริกเป็นส่วนประกอบ
3    D004       ส้มตำไทย        ยำ  อีสาน            4                    15                 1         ตำมะละกอสดกับมะเขือเทศ ถั่วฝักยาว และกุ้งแห้ง ปรุงรสเปรี้ยวหวานเผ็ด
4    D005    ผัดกะเพราไก่       ผัด   กลาง            4                    15                 1            ไก่สับผัดกับกระเพรา พริก กระเทียม รสจัด นิยมทานกับข้าวและไข่ดาว

2. Ingredients (First 5 rows):
  ingredient_id ingredient_name    category  price_per_unit        unit    source  shelf_life_days  calories_per_100g
0         I001      กระเทียม  เครื่องเทศ             60.0    กิโลกรัม   สวนผัก               30               149
1         I002   พริกขี้หนูสด  เครื่องเทศ            120.0    กิโลกรัม   สวนผัก                7                40
2         I003            ข่า  เครื่องเทศ             80.0    กิโลกรัม   สวนผัก               14                51
3         I004        ตะไคร้  เครื่องเทศ             60.0    กิโลกรัม   สวนผัก               14                99
4         I005     ใบมะกรูด  เครื่องเทศ            150.0    กิโลกรัม   สวนผัก                7                80

3. Recipe Ingredients (First 10 rows):
  dish_id ingredient_id amount      unit              notes
0   D001         I018    300      กรัม     กุ้งขนาดกลาง
1   D001         I004      3       ต้น          หั่นท่อน
2   D001         I003      5      แว่น           หั่นบาง
3   D001         I005      5       ใบ              ฉีก
4   D001         I010      3      เม็ด         หั่นแฉลบ
5   D001         I002     10      เม็ด              ทุบ
6   D001         I016      5       ลูก      คั้นเอาแต่น้ำ
7   D001         I031      2  ช้อนโต๊ะ                  
8   D001         I036    1/2   ช้อนชา                  
9   D001         I034      1   ช้อนชา                  

Provide a thorough answer based on the data. Do not include any code in your response.
If you need to calculate something, perform the calculation yourself and provide the result.
If the information is not in the database, politely say so.

To analyze the calories of ต้มยำกุ้ง, you should:
1. Find the dish_id for "ต้มยำกุ้ง" in the thai_dishes dataframe
2. Use that dish_id to find all ingredients in recipe_ingredients dataframe
3. For each ingredient, look up its calories_per_100g in the ingredients dataframe
4. Calculate total calories based on the amount of each ingredient used

Example Python code to perform this analysis:
```python
# Find dish ID
dish_id = dishes_df[dishes_df['dish_name'] == 'ต้มยำกุ้ง']['dish_id'].values[0]

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

print(f"Total estimated calories for ต้มยำกุ้ง: {total_calories:.2f}")
```
```

## ตัวอย่างโปรมต์ที่ 2: ค้นหาส่วนผสมและวิธีทำของอาหารไทย

```
You are a Thai food expert with access to a database of Thai dishes, ingredients and recipes. 
Answer the following question based on the data provided below.

QUESTION: อยากทราบส่วนผสมและขั้นตอนการทำผัดไทย

DATABASE STRUCTURE:
1. Thai Dishes:
dish_id        object
dish_name      object
dish_type      object
region         object
spicy_level     int64
cooking_time_minutes   int64
difficulty_level       int64
description    object

2. Ingredients:
ingredient_id    object
ingredient_name  object
category         object
price_per_unit   float64
unit             object
source           object
shelf_life_days  int64
calories_per_100g int64

3. Recipe Ingredients:
dish_id        object
ingredient_id  object
amount         object
unit           object
notes          object

DATABASE CONTENT:
[ข้อมูลตัวอย่างของตาราง]

Provide a thorough answer based on the data. Do not include any code in your response.
If you need to calculate something, perform the calculation yourself and provide the result.
If the information is not in the database, politely say so.
```

## ตัวอย่างโปรมต์ที่ 3: ค้นหาอาหารจากวัตถุดิบ

```
You are a Thai food expert with access to a database of Thai dishes, ingredients and recipes. 
Answer the following question based on the data provided below.

QUESTION: ฉันมีกุ้ง ตะไคร้ และมะนาว อยากทำอาหารไทยอะไรได้บ้าง?

DATABASE STRUCTURE:
[โครงสร้างตาราง]

DATABASE CONTENT:
[ข้อมูลตัวอย่างของตาราง]

Provide a thorough answer based on the data. Do not include any code in your response.
If you need to calculate something, perform the calculation yourself and provide the result.
If the information is not in the database, politely say so.
```

## ตัวอย่างโปรมต์ที่ 4: คำนวณราคาประมาณการของอาหาร

```
You are a Thai food expert with access to a database of Thai dishes, ingredients and recipes. 
Answer the following question based on the data provided below.

QUESTION: ต้องใช้งบประมาณเท่าไหร่ในการทำแกงเขียวหวานไก่สำหรับ 4 คน?

DATABASE STRUCTURE:
[โครงสร้างตาราง]

DATABASE CONTENT:
[ข้อมูลตัวอย่างของตาราง]

Provide a thorough answer based on the data. Do not include any code in your response.
If you need to calculate something, perform the calculation yourself and provide the result.
If the information is not in the database, politely say so.
```

## ตัวอย่างคำตอบของ Gemini:

เมื่อถูกถามว่า "Show me the calories of ต้มยำกุ้ง" Gemini ควรตอบในลักษณะนี้:

**ตัวอย่างคำตอบที่ดี**:

"ต้มยำกุ้ง (Tom Yum Goong) มีแคลอรี่ประมาณ 320-350 แคลอรี่ต่อถ้วย (1 เสิร์ฟ)

จากการวิเคราะห์ข้อมูลในฐานข้อมูล ต้มยำกุ้งมีส่วนประกอบหลักดังนี้:
- กุ้ง 300 กรัม (คิดเป็นประมาณ 297 แคลอรี่)
- ตะไคร้ 3 ต้น (ประมาณ 30 แคลอรี่)
- ข่า 5 แว่น (ประมาณ 13 แคลอรี่)
- ใบมะกรูด 5 ใบ (ประมาณ 20 แคลอรี่)
- พริกชี้ฟ้าแดง 3 เม็ด (ประมาณ 12 แคลอรี่)
- พริกขี้หนูสด 10 เม็ด (ประมาณ 4 แคลอรี่)
- มะนาว 5 ลูก (ประมาณ 36 แคลอรี่)
- น้ำปลา 2 ช้อนโต๊ะ (ประมาณ 10 แคลอรี่)
- เกลือ และน้ำตาลในปริมาณเล็กน้อย (ประมาณ 20 แคลอรี่)

ต้มยำกุ้งเป็นอาหารที่มีแคลอรี่ไม่สูงมากเมื่อเทียบกับอาหารไทยจานอื่นๆ เนื่องจากเป็นอาหารประเภทต้มที่ใช้น้ำมันน้อย และใช้สมุนไพรหลายชนิดที่มีแคลอรี่ต่ำ"

หมายเหตุ: คุณสามารถปรับโปรมต์เหล่านี้ตามความต้องการของคุณ โดยเพิ่มหรือแก้ไขข้อมูลได้ตามความเหมาะสม เพื่อให้ Gemini สามารถตอบคำถามเกี่ยวกับอาหารไทยได้อย่างถูกต้องและครบถ้วน
