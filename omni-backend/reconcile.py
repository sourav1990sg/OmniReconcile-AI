import pandas as pd
import io
import math

def parse_pos_files(pos_files_data):
    df_list = []
    for filename, file_bytes in pos_files_data:
        try:
            name = (filename or "").lower()
            if name.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            
            # Dynamically map POS columns
            col_map = {}
            for col in df.columns:
                col_str = str(col).lower()
                if 'aggregator order no' in col_str or 'order id' in col_str:
                    col_map[col] = 'Aggregator_Order_ID'
                elif 'my amount' in col_str or 'expected' in col_str:
                    col_map[col] = 'Expected Amount'
                elif col_str == 'date' or col_str == 'invoice date':
                    if 'Date' not in col_map.values():
                        col_map[col] = 'Date'
                elif 'outlet name' in col_str or 'restaurant' in col_str:
                    if 'Outlet' not in col_map.values():
                        col_map[col] = 'Outlet'
                elif 'order from' in col_str or 'platform' in col_str:
                    col_map[col] = 'Platform'

            df = df.rename(columns=col_map)
            
            # Keep required columns
            req_cols = ['Aggregator_Order_ID', 'Expected Amount', 'Date', 'Outlet', 'Platform']
            avail_cols = [c for c in req_cols if c in df.columns]
            df = df[avail_cols].dropna(subset=['Aggregator_Order_ID'])
            
            # Clean ID (remove decimals, cast to string)
            df['Aggregator_Order_ID'] = df['Aggregator_Order_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df['Expected Amount'] = pd.to_numeric(df['Expected Amount'], errors='coerce').fillna(0)
            
            df_list.append(df)
        except Exception as e:
            print(f"Error parsing POS file {filename}: {e}")
            
    if not df_list:
        return pd.DataFrame()
    return pd.concat(df_list, ignore_index=True)

def parse_agg_files(agg_files_data):
    df_list = []
    for filename, file_bytes in agg_files_data:
        try:
            lower_name = (filename or "").lower()
            if not lower_name:
                raise ValueError("Aggregator file is missing a filename.")
            
            # ZOMATO EXTRACTOR
            if 'zomato' in lower_name:
                # Dynamically hunt for the header row
                df_temp = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Order Level', header=None, nrows=15)
                header_idx = 5 # fallback
                for idx, row in df_temp.iterrows():
                    if any('Order ID' in str(val) for val in row.values):
                        header_idx = idx
                        break
                
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Order Level', header=header_idx)
                
                # Dynamically hunt for columns
                id_col = next((c for c in df.columns if 'Order ID' in str(c)), None)
                payout_col = next((c for c in df.columns if 'Order level Payout' in str(c) or 'Net Payout' in str(c)), None)
                
                if id_col and payout_col:
                    df = df[[id_col, payout_col]].rename(columns={id_col: 'Aggregator_Order_ID', payout_col: 'Settled Amount'})
                    df['Platform'] = 'Zomato'
                    df_list.append(df)
                    
            # SWIGGY EXTRACTOR
            elif 'swiggy' in lower_name or 'annexure' in lower_name:
                df = pd.read_csv(io.BytesIO(file_bytes))
                
                # Dynamically hunt for columns
                id_col = next((c for c in df.columns if str(c).strip().lower() in ['order no', 'order id', 'order_id', 'order_no']), None)
                
                # Find the payout column, preferring the final 'Net Payable' amount
                payout_candidates = [c for c in df.columns if 'Net Payable Amount (after' in str(c) or 'Net Payout' in str(c) or 'Settled' in str(c)]
                payout_col = payout_candidates[0] if payout_candidates else None
                
                if id_col and payout_col:
                    df = df[[id_col, payout_col]].rename(columns={id_col: 'Aggregator_Order_ID', payout_col: 'Settled Amount'})
                    df['Platform'] = 'Swiggy'
                    df_list.append(df)
                    
        except Exception as e:
            print(f"Error parsing Aggregator file {filename}: {e}")
            
    if not df_list:
        return pd.DataFrame()
        
    master_df = pd.concat(df_list, ignore_index=True)
    master_df = master_df.dropna(subset=['Aggregator_Order_ID'])
    master_df['Aggregator_Order_ID'] = master_df['Aggregator_Order_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    master_df['Settled Amount'] = pd.to_numeric(master_df['Settled Amount'], errors='coerce').fillna(0)
    return master_df

def run_reconciliation(pos_files_data, agg_files_data):
    # 1. Parse all files into master dataframes
    pos_df = parse_pos_files(pos_files_data)
    agg_df = parse_agg_files(agg_files_data)

    if pos_df.empty:
        raise ValueError(
            "No usable POS rows parsed. Check that Petpooja files include "
            "'Aggregator Order No.' and 'My amount' columns."
        )
    if agg_df.empty:
        raise ValueError(
            "No usable aggregator rows parsed. Ensure Zomato filenames contain "
            "'zomato' and Swiggy filenames contain 'swiggy' or 'annexure', "
            "and that payout columns can be detected."
        )
        
    # 2. Merge data on the exact Order ID
    merged = pd.merge(pos_df, agg_df, on='Aggregator_Order_ID', how='inner')
    
    # 3. Calculate Discrepancy
    merged['Expected Amount'] = pd.to_numeric(merged['Expected Amount'], errors='coerce').fillna(0)
    merged['Settled Amount'] = pd.to_numeric(merged['Settled Amount'], errors='coerce').fillna(0)
    merged['Discrepancy'] = merged['Settled Amount'] - merged['Expected Amount']
    
    # 4. Format Output for Frontend Table
    results = []
    for _, row in merged.iterrows():
        # Clean up date format if it exists
        date_str = str(row.get('Date', 'N/A'))
        
        # Round the numbers for a clean UI
        expected = round(row['Expected Amount'], 2)
        settled = round(row['Settled Amount'], 2)
        discrepancy = round(row['Discrepancy'], 2)
        
        # Status Logic
        if abs(discrepancy) <= 5.00:  # Allow Rs. 5 margin of error for fractional roundings
            status = "Matched"
        else:
            status = "Flagged"
            
        results.append({
            "Date": date_str,
            "Order ID": row['Aggregator_Order_ID'],
            "Platform": row.get('Platform_x', row.get('Platform', 'Unknown')),
            "Outlet": row.get('Outlet', 'Unknown'),
            "Expected Amount": expected,
            "Settled Amount": settled,
            "Discrepancy": discrepancy,
            "Status": status
        })
        
    return results