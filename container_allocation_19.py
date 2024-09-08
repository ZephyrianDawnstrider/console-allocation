import streamlit as st
import pandas as pd
from io import BytesIO

# Constants for classification
PERFECT_CARGO_RATIO = 266
VERY_VOL_CARGO_THRESHOLD = 70
VERY_DENSE_CARGO_THRESHOLD = 750
MAX_DENSE_CARGO_RATIO = 350

def classify_cargo(weight, cbm):
    ratio = weight / cbm
    if ratio == PERFECT_CARGO_RATIO:
        return 'Perfect Cargo'
    elif ratio < VERY_VOL_CARGO_THRESHOLD:
        return 'Very Volumetric Cargo'
    elif ratio < PERFECT_CARGO_RATIO:
        return 'Volumetric Cargo'
    elif ratio > VERY_DENSE_CARGO_THRESHOLD:
        return 'Very Dense Cargo'
    elif ratio > PERFECT_CARGO_RATIO:
        return 'Dense Cargo'
    return 'Undefined'

def process_cfs_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    total_weight = df['WEIGHT'].sum()
    total_cbm = df['CBM'].sum()
    ratio = total_weight / total_cbm
    cargo_type = classify_cargo(total_weight, total_cbm)
    return df, ratio, cargo_type

def filter_and_group_cargo(cargo_df, cfs_console_nos):
    # Drop rows with matching CONSOLE NO. in CFS files
    filtered_df = cargo_df[~cargo_df['CONSOLE NO.'].isin(cfs_console_nos)]
    return filtered_df

def allocate_cargo(cfs_df, cargo_df, max_ratio, cfs_name):
    used_consoles = set(cfs_df['CONSOLE NO.'].unique())
    allocation_statements = []
    
    for console_no in cargo_df['CONSOLE NO.'].unique():
        if console_no in used_consoles:
            continue
        
        console_rows = cargo_df[cargo_df['CONSOLE NO.'] == console_no]
        weight = console_rows['WEIGHT'].sum()
        cbm = console_rows['CBM'].sum()
        
        new_total_weight = cfs_df['WEIGHT'].sum() + weight
        new_total_cbm = cfs_df['CBM'].sum() + cbm
        new_ratio = new_total_weight / new_total_cbm
        
        if new_ratio <= max_ratio:
            # Add all rows for the console to the CFS DataFrame
            cfs_df = pd.concat([cfs_df, console_rows])
            used_consoles.add(console_no)
            allocation_statements.append(f"Console {console_no} should go to {cfs_name}")
    
    return cfs_df, allocation_statements

def convert_df_to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def main():
    st.title("CFS Cargo Allocation")

    # Upload CFS files
    triway_cfs_file = st.file_uploader("Upload TRIWAY CFS File", type="xlsx")
    thirurani_cfs_file = st.file_uploader("Upload THIRURANI CFS File", type="xlsx")

    if triway_cfs_file and thirurani_cfs_file:
        triway_df, triway_ratio, triway_cargo_type = process_cfs_file(triway_cfs_file)
        thirurani_df, thirurani_ratio, thirurani_cargo_type = process_cfs_file(thirurani_cfs_file)
        
        st.write(f"TRIWAY CFS Cargo Type: {triway_cargo_type} ({triway_ratio:.2f} kg/CBM)")
        st.write(f"THIRURANI CFS Cargo Type: {thirurani_cargo_type} ({thirurani_ratio:.2f} kg/CBM)")

        # Upload Cargo Tracking Sheet
        cargo_tracking_file = st.file_uploader("Upload Cargo Tracking Sheet", type="xlsx")
        
        if cargo_tracking_file:
            cargo_df = pd.read_excel(cargo_tracking_file)
            triway_console_nos = triway_df['CONSOLE NO.'].unique()
            thirurani_console_nos = thirurani_df['CONSOLE NO.'].unique()

            filtered_cargo_df = filter_and_group_cargo(cargo_df, list(triway_console_nos) + list(thirurani_console_nos))

            # Allocate cargo to TRIWAY and THIRURANI CFS files
            triway_df, triway_statements = allocate_cargo(triway_df, filtered_cargo_df, MAX_DENSE_CARGO_RATIO, "TRIWAY CFS")
            thirurani_df, thirurani_statements = allocate_cargo(thirurani_df, filtered_cargo_df, MAX_DENSE_CARGO_RATIO, "THIRURANI CFS")
            
            # Combine allocation statements
            allocation_statements = triway_statements + thirurani_statements
            
            # Display the first five allocation statements
            st.write("Cargo Allocation Statements:")
            for statement in allocation_statements[:5]:
                st.write(statement)
            
            # Create download buttons for the updated CFS files
            st.download_button(
                label="Download TRIWAY CFS",
                data=convert_df_to_excel(triway_df),
                file_name='updated_triway_cfs.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            st.download_button(
                label="Download THIRURANI CFS",
                data=convert_df_to_excel(thirurani_df),
                file_name='updated_thirurani_cfs.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

if __name__ == "__main__":
    main()
