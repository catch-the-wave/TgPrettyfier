import json
import os
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Telegram Chat Filter")

st.title("Telegram Chat Filter")
st.subheader("Process your Telegram chat for minimal token usage with Claude")

# File uploader
uploaded_file = st.file_uploader("Upload your Telegram chat JSON file", type=["json"])

if uploaded_file is not None:
    # Load the JSON data
    try:
        data = json.load(uploaded_file)
        messages = data.get('messages', [])
        st.success(f"Loaded {len(messages)} messages from {data.get('name', 'Unknown chat')}")
        
        # Save data to session state for later use
        st.session_state.chat_data = data
        st.session_state.messages = messages
        
        # Settings column layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Filter Settings")
            
            # Export filename
            default_filename = data.get('name', 'telegram_chat') + "_filtered"
            export_filename = st.text_input("Export filename (without extension)", default_filename)
            
            # Include sender names
            include_names = st.checkbox("Include sender names", value=True)
            
            # Include reposts/forwarded messages
            include_reposts = st.checkbox("Include forwarded messages", value=False)
            
            # Include forwarded_from field
            include_forwarded_from = st.checkbox("Include 'forwarded_from' field", value=False)
            
            # Keywords filtering
            st.subheader("Filter by keywords")
            keywords_input = st.text_input("Enter keywords (comma separated)")
            
            if st.button("Apply Filters"):
                # Process the keywords
                keywords = [k.strip().lower() for k in keywords_input.split(',') if k.strip()]
                
                # Filter messages
                filtered_messages = []
                for msg in messages:
                    # Skip forwarded messages if not included
                    if not include_reposts and 'forwarded_from' in msg:
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
                    
                    # Add message to filtered results
                    filtered_msg = {
                        'date': msg.get('date', ''),
                        'from': msg.get('from', '') if include_names else '',
                        'text': text
                    }
                    
                    # Add forwarded_from if the checkbox is checked and it exists
                    if include_forwarded_from and 'forwarded_from' in msg:
                        filtered_msg['forwarded_from'] = msg.get('forwarded_from', '')
                    
                    filtered_messages.append(filtered_msg)
                
                # Save filtered messages to session state
                st.session_state.filtered_messages = filtered_messages
                st.session_state.export_filename = export_filename
                
                # Display counts
                st.success(f"Filtered to {len(filtered_messages)} messages")
        
        with col2:
            if 'filtered_messages' in st.session_state:
                st.subheader("Message Preview")
                
                # Display all filtered messages in a scrollable table
                preview_df = pd.DataFrame(st.session_state.filtered_messages)
                st.dataframe(preview_df, use_container_width=True, height=400)
                
                # Calculate total character count as a rough token estimate
                total_chars = sum(len(str(msg.get('from', ''))) + len(str(msg.get('text', ''))) for msg in st.session_state.filtered_messages)
                st.info(f"Approximate character count: {total_chars} (~{total_chars // 4} tokens)")
                
                # Generate exports
                st.subheader("Export Options")
                
                # Function to generate JSON output
                def generate_json():
                    return json.dumps({
                        'name': data.get('name', 'Unknown chat'),
                        'messages': st.session_state.filtered_messages
                    }, ensure_ascii=False, indent=2)
                
                # Function to generate plain text output
                def generate_text():
                    text_output = ""
                    for msg in st.session_state.filtered_messages:
                        if include_names and msg.get('from'):
                            text_output += f"{msg.get('date', '')}\n{msg.get('from', '')}: {msg.get('text', '')}\n\n"
                        else:
                            text_output += f"{msg.get('date', '')}\n{msg.get('text', '')}\n\n"
                    return text_output
                
                # Download buttons
                col_txt, col_json = st.columns(2)
                with col_txt:
                    st.download_button(
                        "Download as TXT",
                        generate_text(),
                        file_name=f"{st.session_state.export_filename}.txt",
                        mime="text/plain"
                    )
                
                with col_json:
                    st.download_button(
                        "Download as JSON",
                        generate_json(),
                        file_name=f"{st.session_state.export_filename}.json",
                        mime="application/json"
                    )
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

# Footer
st.markdown("---")
st.caption("This app processes Telegram chat exports to optimize them for use with Claude AI.")