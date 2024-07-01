import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Function to process the DataFrame
def process_data(df):
    # Converting pickup_dt datatype to datetime
    df["Date (dd/mm/yyyy)"] = pd.to_datetime(df["Date (dd/mm/yyyy)"], errors='coerce')

    # lock the things we need
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

    # Define a function to create the desired groups based on 1% range
    def get_within_percentage_groups(df, column, percentage=1, min_group_size=15):
        threshold = percentage / 100
        sorted_df = df.sort_values(by=column).reset_index(drop=True)
        group_labels = []
        current_group = []
        start_value = sorted_df[column].iloc[0]

        group_index = 0
        for i, value in enumerate(sorted_df[column]):
            if abs(value - start_value) <= threshold * start_value:
                current_group.append(i)
            else:
                if len(current_group) >= min_group_size:
                    group_labels.extend([group_index] * len(current_group))
                    group_index += 1
                else:
                    group_labels.extend([None] * len(current_group))

                current_group = [i]
                start_value = value

        # Assign remaining items to the current group
        if len(current_group) >= min_group_size:
            group_labels.extend([group_index] * len(current_group))
        else:
            group_labels.extend([None] * len(current_group))

        sorted_df['GroupLabel'] = group_labels
        return sorted_df.dropna(subset=['GroupLabel'])
    
    # Group the DataFrame by the custom groups
    test_column = 'Actual_Speed_rpm (RPM)'
    df_with_groups = get_within_percentage_groups(df, test_column)
    df_with_groups['GroupLabel'] = df_with_groups['GroupLabel'].astype(int)

    # Define function to calculate group averages
    def calculate_group_averages(df, group_column='GroupLabel', float_columns=float_columns, non_float_columns=non_float_columns):
        grouped = df.groupby(group_column)
        non_float_first_values = grouped[non_float_columns].first()
        float_averages = grouped[float_columns].mean()
        result = non_float_first_values.join(float_averages)
        return result

    # Calculate the result DataFrame
    result_df = calculate_group_averages(df_with_groups)

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
st.title('CSV File Processor')

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
