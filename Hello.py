# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import streamlit as st
from PIL import Image
import pytesseract
import pandas as pd
import re
import base64
import mysql.connector

# Set Tesseract executable path for GitHub Codespaces
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  # Update the path if necessary

# mydb = mysql.connector.connect(
#   host="sql6.freemysqlhosting.net",
#   user="sql6690717",
#   password="WxrvC5imVY",
#   database="sql6690717"
# )

config = {
    'user': 'sql6690717',
    'password': 'WxrvC5imVY',
    'host': 'sql6.freemysqlhosting.net',
    'database': 'sql6690717',
    'raise_on_warnings': True
}


def check_table_exists(table_name):
    # Connect to the MySQL database
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    # Query to check if the table exists
    query = """
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = %s
    AND table_name = %s
    """
    cursor.execute(query, (config['database'], table_name))
    result = cursor.fetchone()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # Return True if the table exists, False otherwise
    return result[0] > 0


def create_table_if_not_exists():
    # Connect to the MySQL database
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    # SQL query to create the table if it doesn't exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS card_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        business_name VARCHAR(255),
        email VARCHAR(255),
        phone_number VARCHAR(20),
        address VARCHAR(255)
    );
    """
    cursor.execute(create_table_query)

    # Check for warnings
    cursor.execute("SHOW WARNINGS")
    warnings = cursor.fetchall()
    for warning in warnings:
        if warning[2] == 1050: # Warning code for "Table already exists"
            print("Table 'card_details' already exists.")

    # Commit the changes and close the connection
    cnx.commit()
    cursor.close()
    cnx.close()


def insert_into_database(data):
    # Connect to the MySQL database
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    # Insert the data into the database
    query = """INSERT INTO card_details (business_name, email, phone_number, address)
               VALUES (%s, %s, %s, %s)"""
    cursor.execute(query, (data['business_name'], data['email'], data['phone_number'], data['address']))

    # Commit the changes and close the connection
    cnx.commit()
    cursor.close()
    cnx.close()


def update_record(id, business_name, email, phone_number, address):
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    update_query = """UPDATE card_details
                      SET business_name = %s, email = %s, phone_number = %s, address = %s
                      WHERE id = %s"""
    cursor.execute(update_query, (business_name, email, phone_number, address, id))
    cnx.commit()
    cursor.close()
    cnx.close()


def display_and_edit_records():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    cursor.execute("SELECT * FROM card_details")
    records = cursor.fetchall()
    cursor.close()
    cnx.close()

    for index, record in enumerate(records):
        id, business_name, email, phone_number, address = record
        st.subheader(f"Record ID: {id}")
        new_business_name = st.text_input(f"Business Name {id}", business_name, key=f"business_name_{id}")
        new_email = st.text_input(f"Email {id}", email, key=f"email_{id}")
        new_phone_number = st.text_input(f"Phone Number {id}", phone_number, key=f"phone_number_{id}")
        new_address = st.text_input(f"Address {id}", address, key=f"address_{id}")
        if st.button(f"Update Record {id}", key=f"update_button_{id}"):
            update_record(id, new_business_name, new_email, new_phone_number, new_address)
            st.success(f"Record {id} updated successfully.")


def delete_from_database(id):
    # Connect to the MySQL database
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    # SQL query to delete the entry with the given ID
    delete_query = "DELETE FROM card_details WHERE id = %s"
    cursor.execute(delete_query, (id,))

    # Commit the changes and close the connection
    cnx.commit()
    cursor.close()
    cnx.close()


def extract_info_from_image(image):
    # Use pytesseract to extract text from the image
    text = pytesseract.image_to_string(image)
    return text


def structure_data(text):
    # Refined patterns for email and address formats
    # Adjusted to match the specific formats mentioned

    # Business Name: Capture a sequence of characters that is likely to be the name
    business_name = re.search(r'\b[A-Za-z\s&]+(?=[\s.,:;])', text)

    # Email: Capture specific email format (e.g., hello@reallygreatsite.com)
    email = re.search(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+', text)

    # Phone Number: Capture common US phone number formats
    phone_number = re.search(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', text)

    # Address: Capture a sequence of characters that might be an address, in a specific format (e.g.,  123 Anywhere St., Any City)
    # Note: This pattern assumes addresses are typically followed by a comma, which might not always be the case.
    address = re.search(r'\b\d+\s+[a-zA-Z\s,.]+,\s*[a-zA-Z\s]+\b', text)

    return {
        'Business Name': business_name.group() if business_name else None,
        'Email': email.group() if email else None,
        'Phone Number': phone_number.group() if phone_number else None,
        'Address': address.group() if address else None
    }


def edit_data(data, index):
    edited_data = {}
    for key, value in data.items():
        unique_key = f"{key}_{index}"
        edited_value = st.text_input(f"Edit {key}:", value, key=unique_key)
        edited_data[key] = edited_value.strip() if edited_value else None
    return edited_data


def main():
    if not check_table_exists('card_details'):
        create_table_if_not_exists()

    st.title("Business Card OCR App")

    # Allow multiple file uploads or folder uploads
    uploaded_files_or_folder = st.file_uploader("Upload business card images or folder", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if uploaded_files_or_folder:
        # Check if a folder is uploaded
        if len(uploaded_files_or_folder) == 1 and os.path.isdir(uploaded_files_or_folder[0].name):
            folder_path = uploaded_files_or_folder[0].name
            uploaded_files = [Image.open(os.path.join(folder_path, filename)) for filename in os.listdir(folder_path) if filename.lower().endswith(('.jpg', '.jpeg', '.png'))]
        else:
            uploaded_files = [Image.open(uploaded_file) for uploaded_file in uploaded_files_or_folder]

        # Initialize an empty list to store results
        results_list = []

        # Process each uploaded image
        for idx, image in enumerate(uploaded_files):
            st.image(image, caption=f"Uploaded Image {idx+1}", use_column_width=True)

            # Extract information using OCR
            extracted_text = extract_info_from_image(image)

            # Display the extracted text
            st.subheader(f"Extracted Information for Image {idx+1}:")
            st.text(extracted_text)

            # Structure the data
            structured_data = structure_data(extracted_text)

            # Edit the data
            st.subheader(f"Edit Information for Image {idx+1}:")
            edited_data = edit_data(structured_data, idx)
            # st.subheader(edited_data)

            # Display the edited data
            st.subheader(f"Edited Data for Image {idx+1}:")
            business_name = edited_data.get('Business Name', None)
            email = edited_data.get('Email', None)
            phone_number = edited_data.get('Phone Number', None)
            address = edited_data.get('Address', None)

            # Check if the key exists before displaying
            if business_name is not None:
                st.text("Business Name: {}".format(business_name))
            if email is not None:
                st.text("Email: {}".format(email))
            if phone_number is not None:
                st.text("Phone Number: {}".format(phone_number))
            if address is not None:
                st.text("Address: {}".format(address))

            # Append edited results to the list
            results_list.append({
                "business_name": business_name,
                "email": email,
                "phone_number": phone_number,
                "address": address
            })

            # Force Streamlit to update the display
            st.write('')

        # Insert the data into the MySQL database
        insert_into_database(results_list[-0])

    # Add a button to view the data in the database
    st.subheader("View Data in Database")
    # view_data_button = st.button("View Data in Database")
    if True:
        # Connect to the MySQL database
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()

        # Query the database
        query = "SELECT * FROM card_details"
        cursor.execute(query)

        # Fetch all the rows
        rows = cursor.fetchall()

        # Display the data with a delete button for each entry
        for row in rows:
            st.write(row)
            if st.button(f"Delete Entry {row[0]}"):
                delete_from_database(row[0])
                st.success(f"Entry {row[0]} deleted successfully.")

        # Close the cursor and connection
        cursor.close()
        cnx.close()
    display_and_edit_records()


if __name__ == "__main__":
    main()
