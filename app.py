import json
import os
import re
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Telegram JSON Prettifier")
st.title("Telegram JSON Prettifier")

# File uploader
uploaded_file = st.file_uploader("Upload your Telegram chat JSON file", type=["json"])

if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)
        messages = data.get('messages', [])
        st.session_state.chat_data = data
        st.session_state.raw_messages = messages

        # Process messages
        processed_messages = []
        for msg in messages:
            text = msg.get('text', '')
            if isinstance(text, list):
                extracted_text = ""
                for item in text:
                    if isinstance(item, str):
                        extracted_text += item
                    elif isinstance(item, dict) and 'text' in item:
                        extracted_text += item['text']
                text = extracted_text

            processed_msg = {
                'text': text,
                'date': msg.get('date', ''),
                'from': msg.get('from', '')
            }

            if 'forwarded_from' in msg:
                processed_msg['forwarded_from'] = msg.get('forwarded_from', '')

            processed_messages.append(processed_msg)

        # UI Filters
        st.subheader("Main Filters")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            exclude_forwarded = st.checkbox("Exclude forwarded messages", value=False)
        with col2:
            hide_from = st.checkbox("Hide 'from' field", value=True)
        with col3:
            hide_senders = st.checkbox("Hide senders", value=False)
        with col4:
            hide_time = st.checkbox("Hide time", value=False)

        # Add skip empty messages checkbox
        skip_empty = st.checkbox("Skip empty messages", value=False, help="Skip messages with empty text")

        col1, col2 = st.columns(2)
        with col1:
            keywords_input = st.text_input("Filter by keywords (comma separated)")
        with col2:
            save_from_msg = st.number_input("Filter from message #", min_value=0, max_value=len(processed_messages), value=0)

        # Apply Filters
        if st.button("Apply Filters"):
            filtered_messages = []
            keywords = [k.strip().lower() for k in keywords_input.split(',') if k.strip()]

            for msg in messages:
                text = msg.get('text', '')
                if isinstance(text, list):
                    extracted_text = ""
                    for item in text:
                        if isinstance(item, str):
                            extracted_text += item
                        elif isinstance(item, dict) and 'text' in item:
                            extracted_text += item['text']
                    text = extracted_text

                # Skip empty messages if option is selected
                if skip_empty and (text == "" or text is None):
                    continue

                # Filter forwarded
                if exclude_forwarded and 'forwarded_from' in msg:
                    continue

                # Filter by keywords
                if keywords:
                    if not any(k in text.lower() for k in keywords):
                        continue

                filtered_msg = {'text': text}

                if not hide_time:
                    filtered_msg['date'] = msg.get('date', '')

                if not hide_from:
                    filtered_msg['from'] = msg.get('from', '')

                if not exclude_forwarded and 'forwarded_from' in msg:
                    filtered_msg['forwarded_from'] = msg.get('forwarded_from', '')

                filtered_messages.append(filtered_msg)

            # Cut from starting message #
            if save_from_msg > 0:
                filtered_messages = filtered_messages[save_from_msg:]

            # Show results
            filtered_df = pd.DataFrame(filtered_messages)
            st.dataframe(filtered_df, use_container_width=True, height=300)

            total_chars = sum(len(str(m.get('text', ''))) for m in filtered_messages)
            if not hide_from:
                total_chars += sum(len(str(m.get('from', ''))) for m in filtered_messages)
            if not hide_time:
                total_chars += sum(len(str(m.get('date', ''))) for m in filtered_messages)

            col1, col2 = st.columns(2)
            with col1:
                st.success(f"Filtered to {len(filtered_messages)} messages")
            with col2:
                st.info(f"Approx. character count: {total_chars} (~{total_chars // 4} tokens)")

            # === EXPORT FILENAME SECTION ===
            default_filename = data.get('name', 'telegram_chat')

            keywords_clean = [re.sub(r'[^\w\-]', '', k) for k in keywords]
            keywords_part = ", ".join(keywords_clean)
            if keywords_part:
                auto_filename = f"{default_filename}_[{keywords_part}]"
            else:
                auto_filename = default_filename

            export_filename = st.text_input("Export filename (without extension)", value=auto_filename)

            # === EXPORT FUNCTIONS ===
            def generate_json():
                return json.dumps({
                    'name': data.get('name', 'Unknown chat'),
                    'messages': filtered_messages
                }, ensure_ascii=False, indent=2)

            def generate_text():
                text_output = ""
                for msg in filtered_messages:
                    date = msg.get('date', '')
                    sender = msg.get('from', '')
                    forwarded = f" [Forwarded from: {msg.get('forwarded_from', '')}]" if 'forwarded_from' in msg else ''
                    body = msg.get('text', '')

                    if 'from' in msg and not hide_senders:
                        text_output += f"{date}\n{sender}{forwarded}: {body}\n\n\n" if date else f"{sender}{forwarded}: {body}\n\n\n"
                    else:
                        text_output += f"{date}\n{forwarded + ' ' if forwarded else ''}{body}\n\n\n" if date else f"{forwarded + ' ' if forwarded else ''}{body}\n\n\n"
                return text_output

            # === DOWNLOAD BUTTONS ===
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