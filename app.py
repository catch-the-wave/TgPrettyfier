import json
import os
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Telegram Json prettifier")

st.title("Telegram Json prettifier")
# st.subheader("Process your Telegram chat for minimal token usage with Claude")

# File uploader
uploaded_file = st.file_uploader("Upload your Telegram chat JSON file", type=["json"])

if uploaded_file is not None:
    # Load the JSON data
    try:
        data = json.load(uploaded_file)
        messages = data.get('messages', [])
        # st.success(f"Loaded {len(messages)} messages from {data.get('name', 'Unknown chat')}")
        
        # Save data to session state for later use
        st.session_state.chat_data = data
        st.session_state.raw_messages = messages
        
        # Process messages for display
        processed_messages = []
        for msg in messages:
            # Get the text content
            text = msg.get('text', '')
            if isinstance(text, list):
                # If text is a list of entities, extract just the text parts
                extracted_text = ""
                for item in text:
                    if isinstance(item, str):
                        extracted_text += item
                    elif isinstance(item, dict) and 'text' in item:
                        extracted_text += item['text']
                text = extracted_text
            
            # Add to processed messages in the desired order
            processed_msg = {
                'text': text,
                'date': msg.get('date', ''),
                'from': msg.get('from', '')
            }
            
            if 'forwarded_from' in msg:
                processed_msg['forwarded_from'] = msg.get('forwarded_from', '')
            
            processed_messages.append(processed_msg)
        
        # Filter settings in horizontal layout
        # st.subheader("Filter Settings")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            exclude_forwarded = st.checkbox("Exclude forwarded messages", value=False)
        
        with col2:
            hide_from = st.checkbox("Hide 'from' field", value=True)
        
        with col3:
            hide_senders = st.checkbox("Hide senders", value=False)
            
        with col4:
            hide_time = st.checkbox("Hide time", value=False)
        
        # Keywords filtering
        keywords_input = st.text_input("Filter by keywords (comma separated, leave empty to show all)")

        # Define export filename here (moved up from its previous position)
        default_filename = data.get('name', 'telegram_chat') + "_filtered"
        export_filename = default_filename  # Initialize with default
        
        # Process filter button
        if st.button("Apply Filters"):
            # Process the keywords
            keywords = [k.strip().lower() for k in keywords_input.split(',') if k.strip()]
            
            # Filter messages
            filtered_messages = []
            for msg in messages:
                # Skip forwarded messages if excluded
                if exclude_forwarded and 'forwarded_from' in msg:
                    continue
                
                # Get the text content
                text = msg.get('text', '')
                if isinstance(text, list):
                    # If text is a list of entities, extract just the text parts
                    extracted_text = ""
                    for item in text:
                        if isinstance(item, str):
                            extracted_text += item
                        elif isinstance(item, dict) and 'text' in item:
                            extracted_text += item['text']
                    text = extracted_text
                
                # Filter by keywords if they are provided
                if keywords:
                    if not any(keyword.lower() in text.lower() for keyword in keywords):
                        continue
                
                # Prepare the filtered message with preferred order
                filtered_msg = {
                    'text': text
                }
                
                # Add date if not hidden
                if not hide_time:
                    filtered_msg['date'] = msg.get('date', '')
                
                # Add forwarded_from if it exists and we're including forwarded messages
                if not exclude_forwarded and 'forwarded_from' in msg:
                    filtered_msg['forwarded_from'] = msg.get('forwarded_from', '')
                
                # Handle from field based on settings
                if not hide_from:
                    filtered_msg['from'] = msg.get('from', '')
                
                filtered_messages.append(filtered_msg)
            
            # Save filtered messages to session state
            st.session_state.filtered_messages = filtered_messages
            st.session_state.export_filename = export_filename
            
            # Display filtered messages in a scrollable table
            filtered_df = pd.DataFrame(filtered_messages)
            st.dataframe(filtered_df, use_container_width=True, height=300)
            
            # Calculate total character count as a rough token estimate
            total_chars = sum(len(str(msg.get('text', ''))) for msg in filtered_messages)
            if not hide_from:
                total_chars += sum(len(str(msg.get('from', ''))) for msg in filtered_messages)
            if not hide_time:
                total_chars += sum(len(str(msg.get('date', ''))) for msg in filtered_messages)

            col1, col2 = st.columns(2)

            with col1:
                st.success(f"Filtered to {len(filtered_messages)} messages")
            with col2:
                st.info(f"Approximate character count: {total_chars} (~{total_chars // 4} tokens)")
            
            # Generate exports
            st.subheader("Export Options")
            
            # Allow user to customize export filename
            export_filename = st.text_input("Export filename (without extension)", value=default_filename)
            
            # Function to generate JSON output
            def generate_json():
                return json.dumps({
                    'name': data.get('name', 'Unknown chat'),
                    'messages': filtered_messages
                }, ensure_ascii=False, indent=2)
            
            # Function to generate text output
            def generate_text():
                text_output = ""
                for msg in filtered_messages:
                    # Add date if not hidden
                    if 'date' in msg:
                        date_line = msg.get('date', '')
                    else:
                        date_line = ""
                    
                    # Add forwarded_from info if included
                    forwarded_info = ""
                    if 'forwarded_from' in msg:
                        forwarded_info = f" [Forwarded from: {msg.get('forwarded_from', '')}]"
                    
                    # Include sender if not hidden
                    if 'from' in msg and not hide_senders:
                        if date_line:
                            text_output += f"{date_line}\n{msg.get('from', '')}{forwarded_info}: {msg.get('text', '')}\n\n"
                        else:
                            text_output += f"{msg.get('from', '')}{forwarded_info}: {msg.get('text', '')}\n\n"
                    else:
                        if date_line:
                            text_output += f"{date_line}\n{forwarded_info + ' ' if forwarded_info else ''}{msg.get('text', '')}\n\n"
                        else:
                            text_output += f"{forwarded_info + ' ' if forwarded_info else ''}{msg.get('text', '')}\n\n"
                return text_output

            # Download buttons
            col_txt, col_json = st.columns(2)
            with col_txt:
                st.download_button(
                    "Download as TXT",
                    generate_text(),
                    file_name=f"{export_filename}.txt",
                    mime="text/plain"
                )
            
            with col_json:
                st.download_button(
                    "Download as JSON",
                    generate_json(),
                    file_name=f"{export_filename}.json",
                    mime="application/json"
                )
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

# Footer
st.markdown("---")
st.caption("This app processes Telegram chat exports to optimize them for use with Claude AI.")