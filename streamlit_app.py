import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Function to process the DataFrame
def process_data(df):
    # Converting Date datatype to datetime
    df["Date (dd/mm/yyyy)"] = pd.to_datetime(df["Date (dd/mm/yyyy)"], errors='coerce')

    # Lock the things we need
    columns_of_interest = [
        'Date (dd/mm/yyyy)', 'Time (hh:mm:ss:msec)', 'Actual_Speed_rpm (RPM)', 'Actual_Torque (Nm)', 
        'Actual_Power (kW)', 'PA DC_Voltage (V)', 'PA DC_Current (Amp)', 'PA DC_Active Power (Watt)', 
        'PA AC_Voltage_SUM (V)', 'PA AC_Current_SUM (Amp)', 'PA AC_Active Power_SUM (Watt)', 
        'PA AC_Power Factor_SUM (PF)', 'Controller Efficiency', 'Motor Efficiency', 'System Efficiency'
    ]
    df = df.loc[:, columns_of_interest]

    # Identifying float and non-float columns
    float_columns = df.select_dtypes(include='float64').columns.tolist()
    non_float_columns = df.select_dtypes(exclude='float64').columns.tolist()

    def calculate_average_sequential(df, key_columns, percentage=1, min_group_size=15):
        grouped_data = []
        current_group = []
        start_values = [None, None]

        for index, row in df.iterrows():
            values = [row[key_col] for key_col in key_columns]
            
            if (start_values[0] is None or abs(values[0] - start_values[0]) <= (percentage / 100) * start_values[0]) and \
               (start_values[1] is None or abs(values[1] - start_values[1]) <= (percentage / 100) * start_values[1]):
                current_group.append(row)
                if start_values[0] is None:
                    start_values = values
            else:
                if len(current_group) >= min_group_size:
                    # Calculate the average for the current group
                    group_df = pd.DataFrame(current_group)
                    averaged_data = group_df.mean(numeric_only=True)
                    averaged_data = pd.concat([group_df.iloc[0][non_float_columns], averaged_data])
                    grouped_data.append(averaged_data)
                start_values = values
                current_group = [row]

        if len(current_group) >= min_group_size:
            group_df = pd.DataFrame(current_group)
            averaged_data = group_df.mean(numeric_only=True)
            averaged_data = pd.concat([group_df.iloc[0][non_float_columns], averaged_data])
            grouped_data.append(averaged_data)

        if grouped_data:
            return pd.DataFrame(grouped_data)
        else:
            return pd.DataFrame(columns=columns_of_interest)

    # Calculate averages based on Actual_Speed_rpm (RPM) and Actual_Torque (Nm)
    key_columns = ['Actual_Speed_rpm (RPM)', 'Actual_Torque (Nm)']
    result_df = calculate_average_sequential(df, key_columns)

    # Round specific columns
    columns_to_round_0 = [
        'Actual_Speed_rpm (RPM)', 'PA DC_Voltage (V)', 'PA DC_Current (Amp)', 'PA DC_Active Power (Watt)', 
        'PA AC_Active Power_SUM (Watt)', 'Controller Efficiency', 'Motor Efficiency', 'System Efficiency'
    ]
    columns_to_round_2 = [
        'Actual_Torque (Nm)', 'Actual_Power (kW)', 'PA AC_Current_SUM (Amp)', 'PA AC_Voltage_SUM (V)', 'PA AC_Power Factor_SUM (PF)'
    ]
    result_df[columns_to_round_0] = result_df[columns_to_round_0].round(0)
    result_df[columns_to_round_2] = result_df[columns_to_round_2].round(2)

    # Replace NaN/Infinity values with a placeholder (e.g., empty string or specific value)
    result_df = result_df.replace([np.nan, np.inf, -np.inf], '')

    return result_df

# Function to convert DataFrame to Excel and return as a downloadable link
def to_excel_download_link(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Results')
        workbook = writer.book
        worksheet = writer.sheets['Results']
        
        # Define a date format and a center alignment format
        center_format = workbook.add_format({'align': 'center'})
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'center'})
        
        # Apply formats to all cells
        for row_num in range(1, len(df) + 1):
            for col_num in range(len(df.columns)):
                cell_value = df.iloc[row_num - 1, col_num]
                if pd.api.types.is_datetime64_any_dtype(df.iloc[:, col_num]):
                    worksheet.write_datetime(row_num, col_num, cell_value, date_format)
                else:
                    worksheet.write(row_num, col_num, cell_value, center_format)
        
        # Adjust the width of each column
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
    processed_data = output.getvalue()
    return processed_data

# Streamlit app
st.title('AMeM CSV File Processor')

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    # Read the uploaded CSV file
    df = pd.read_csv(uploaded_file)

    # Display the raw data
    st.subheader("Raw Data")
    st.write(df.head())

    # Show descriptive statistics of the data
    st.subheader("Data Description")
    st.write(df.describe())

    # Process the data
    try:
        processed_df = process_data(df)
        st.subheader("Processed Data")
        st.write(processed_df.head())

        # Prepare the downloadable Excel file
        st.subheader("Download Processed Data as Excel")
        processed_data = to_excel_download_link(processed_df)
        st.download_button(
            label="Download Excel file",
            data=processed_data,
            file_name="Processed_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"An error occurred: {e}")
