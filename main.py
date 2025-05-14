from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Personalized Email Outreach Agent", layout="wide")
st.title("Personalized Email Outreach Agent")

# Store user input to persist across interactions
if 'course_details' not in st.session_state:
    st.session_state['course_details'] = ''
if 'persona' not in st.session_state:
    st.session_state['persona'] = ''
if 'user_df' not in st.session_state:
    st.session_state['user_df'] = None

# Collect course details from the user
st.header("Step 1: Enter Course Details")
st.session_state['course_details'] = st.text_area("Course Details", value=st.session_state['course_details'])

# Collect the target user persona
st.header("Step 2: Enter User Persona")
st.session_state['persona'] = st.text_area("User Persona", value=st.session_state['persona'])

# Upload the Excel file containing target users
st.header("Step 3: Upload Target Users Excel (with LinkedIn URLs)")
user_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if user_file:
    try:
        df = pd.read_excel(user_file)
        st.session_state['user_df'] = df
        st.success(f"Uploaded {user_file.name} successfully!")
        st.subheader("Preview of Uploaded Users:")
        st.dataframe(df.head(10), use_container_width=True)
        if 'linkedin' in [c.lower() for c in df.columns]:
            st.info("Found LinkedIn column.")
        else:
            st.warning("No LinkedIn column found. Please ensure your Excel has a column for LinkedIn URLs.")
    except Exception as e:
        st.error(f"Failed to read Excel file: {e}")
else:
    st.session_state['user_df'] = None

st.markdown("---")

from app.agents.workflow import OutreachWorkflow
import io

# NOTE: If you get a 401 Unauthorized from Bright Data API, check your BRIGHTDATA_API_KEY in .env or Streamlit secrets!

# Store results for later use
if 'results' not in st.session_state:
    st.session_state['results'] = None

# LinkedIn Login Details section removed. No login required with Bright Data API.

progress_placeholder = st.empty()
error_placeholder = st.empty()

if st.button("Start Workflow"):
    if not st.session_state['course_details'] or not st.session_state['persona'] or st.session_state['user_df'] is None:
        st.error("Please fill in all fields and upload a valid Excel file before starting.")
    else:
        user_df = st.session_state['user_df']
        if user_df.shape[0] == 0:
            st.error("No rows found in the uploaded file.")
        else:
            import time
            import math
            # Estimate wait time: 25s per batch of 10 LinkedIn URLs
            num_urls = user_df.shape[0]
            batch_size = 10
            est_batch_time = 25  # seconds per batch
            total_batches = math.ceil(num_urls / batch_size)
            est_total_time = total_batches * est_batch_time
            with st.spinner(f"Fetching LinkedIn profiles and generating emails... Estimated time: {est_total_time} seconds for {num_urls} profiles."):
                start_time = time.time()
                workflow = OutreachWorkflow(db_type='supabase')
                try:
                    progress_placeholder.progress(0, text=f"Processing 0/{user_df.shape[0]}...")
                    results = workflow.run(
                        st.session_state['course_details'],
                        st.session_state['persona'],
                        user_df
                    )
                    st.session_state['results'] = results
                except Exception as e:
                    error_placeholder.error(f"Error processing rows: {e}")
                finally:
                    elapsed = int(time.time() - start_time)
                    st.success(f"Done! Actual time: {elapsed} seconds.")
                progress_placeholder.empty()
                error_placeholder.empty()

if st.session_state['results'] is not None:
    st.success(f"Generated {len(st.session_state['results'])} personalized emails!")

    # --- Gmail Credentials Section (show only after workflow) ---
    if 'sender_email' not in st.session_state:
        st.session_state['sender_email'] = ''
    if 'app_password' not in st.session_state:
        st.session_state['app_password'] = ''
    # Only render these fields here, after results, and with unique keys
    sender_email = st.text_input("Your Gmail Address (sender)", value=st.session_state['sender_email'], key="sender_email_input_results")
    st.session_state['sender_email'] = sender_email
    def gmail_label():
        return ("Gmail App Password ("
                "<a href='#' style='color:#1a73e8;text-decoration:underline;' onclick=\"window.parent.postMessage('show_gmail_popup','*')\">see instructions</a>)", True)
    label_html, _ = gmail_label()
    st.markdown(label_html, unsafe_allow_html=True)
    app_password = st.text_input("Gmail App Password", type="password", value=st.session_state['app_password'], key="app_password_input_results", help="Click 'see instructions' for Gmail App Password setup.")
    st.session_state['app_password'] = app_password
    import streamlit.components.v1 as components
    if 'show_gmail_popup' not in st.session_state:
        st.session_state['show_gmail_popup'] = False
    components.html('''
    <script>
    window.addEventListener('message', function(event) {
        if (event.data === 'show_gmail_popup') {
            window.parent.streamlitSend({type:'streamlit:setComponentValue', value:true, key:'show_gmail_popup'});
        }
    });
    </script>
    ''', height=0)
    if st.session_state.get('show_gmail_popup', False):
        with st.container():
            st.info("**Gmail App Password Instructions**")
            show_gmail_instructions()
            if st.button("Close Instructions", key="close_gmail_popup"):
                st.session_state['show_gmail_popup'] = False
    # --- End Gmail Credentials Section ---

    # Show Send Emails button after credentials are entered
    if sender_email and app_password:
        send_status = st.empty()
        log_area = st.empty()
        if st.button("Send Emails", key="send_emails_button_results"):
            import smtplib
            from email.mime.text import MIMEText
            import traceback
            successes = []
            failures = []
            logs = []
            try:
                logs.append("Connecting to Gmail SMTP server...")
                log_area.info("\n".join(logs))
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    logs.append(f"Logging in as {sender_email}...")
                    log_area.info("\n".join(logs))
                    server.login(sender_email, app_password)
                    logs.append("Login successful. Sending emails...")
                    log_area.info("\n".join(logs))
                    for idx, row in preview_df.iterrows():
                        recipient = row['Email']
                        subject = row['Email Subject']
                        body = row['Email Body']
                        try:
                            logs.append(f"Sending to {recipient} (subject: {subject})...")
                            log_area.info("\n".join(logs))
                            msg = MIMEText(body, "plain")
                            msg["Subject"] = subject or "Personalized Outreach"
                            msg["From"] = sender_email
                            msg["To"] = recipient
                            server.sendmail(sender_email, recipient, msg.as_string())
                            successes.append(recipient)
                            logs.append(f"✅ Sent to {recipient}")
                        except Exception as e:
                            failures.append((recipient, str(e)))
                            logs.append(f"❌ Failed to send to {recipient}: {e}")
                        log_area.info("\n".join(logs))
                    logs.append("All emails processed.")
                    log_area.info("\n".join(logs))
            except Exception as e:
                logs.append(f"Critical error: {e}\n{traceback.format_exc()}")
                log_area.error("\n".join(logs))
            send_status.success(f"Sent {len(successes)} emails successfully.")
            if failures:
                send_status.error(f"Failed to send to: {', '.join([f[0] for f in failures])}")


        try:
            logs.append("Connecting to Gmail SMTP server...")
            log_area.info("\n".join(logs))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                logs.append("Logging in as {}...".format(sender_email))
                log_area.info("\n".join(logs))
                server.login(sender_email, app_password)
                logs.append("Login successful. Sending emails...")
                log_area.info("\n".join(logs))
                for idx, row in preview_df.iterrows():
                    recipient = row['Email']
                    subject = row['Email Subject']
                    body = row['Email Body']
                    try:
                        logs.append(f"Sending to {recipient} (subject: {subject})...")
                        log_area.info("\n".join(logs))
                        msg = MIMEText(body, "plain")
                        msg["Subject"] = subject or "Personalized Outreach"
                        msg["From"] = sender_email
                        msg["To"] = recipient
                        server.sendmail(sender_email, recipient, msg.as_string())
                        successes.append(recipient)
                        logs.append(f"✅ Sent to {recipient}")
                    except Exception as e:
                        failures.append((recipient, str(e)))
                        logs.append(f"❌ Failed to send to {recipient}: {e}")
                    log_area.info("\n".join(logs))
                logs.append("All emails processed.")
                log_area.info("\n".join(logs))
        except Exception as e:
            logs.append(f"Critical error: {e}\n{traceback.format_exc()}")
            log_area.error("\n".join(logs))
        send_status.success(f"Sent {len(successes)} emails successfully.")
        if failures:
            send_status.error(f"Failed to send to: {', '.join([f[0] for f in failures])}")

    def split_subject_body(draft):
        if draft and ("\n" in draft or "\r" in draft):
            first_line, *rest = draft.splitlines()
            # Remove 'subject:' or similar prefix from the subject line if present
            subject = first_line.strip()
            if subject.lower().startswith('subject:'):
                subject = subject[len('subject:'):].strip()
            return subject, "\n".join(rest).strip()
        subject = draft.strip()
        if subject.lower().startswith('subject:'):
            subject = subject[len('subject:'):].strip()
        return subject, ""

    preview_df = pd.DataFrame([
        {
            'Name': r.get('name'),
            'Email': r.get('email'),
            'Email Subject': split_subject_body(r.get('email_draft'))[0],
            'Email Body': split_subject_body(r.get('email_draft'))[1],
        } for r in st.session_state['results']
    ])
    st.dataframe(preview_df, use_container_width=True)
    csv = preview_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results as CSV", data=csv, file_name="personalized_emails.csv", mime="text/csv", key="download_csv_button")

    st.markdown("---")
    st.subheader("Send Drafted Emails via Gmail")

    # --- Gmail Credentials Section (moved here) ---
    import streamlit.components.v1 as components
    if 'sender_email' not in st.session_state:
        st.session_state['sender_email'] = ''
    if 'app_password' not in st.session_state:
        st.session_state['app_password'] = ''
    sender_email = st.text_input("Your Gmail Address (sender)", value=st.session_state['sender_email'], key="sender_email_input")
    st.session_state['sender_email'] = sender_email

    def show_gmail_instructions():
        st.markdown("""
**How to create a Gmail App Password:**
1. Go to your Google Account.
2. Select **Security**.
3. Under "Signing in to Google," select **2-Step Verification**.
4. At the bottom of the page, select **App passwords**.
5. Enter a name that helps you remember where you’ll use the app password.
6. Select **Generate**.
7. To enter the app password, follow the instructions on your screen. The app password is the 16-character code that generates on your device.
8. Select **Done**.

Alternatively, you can create an app password by logging in to your Google account and going to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
        """)

    if 'show_gmail_popup' not in st.session_state:
        st.session_state['show_gmail_popup'] = False

    def gmail_label():
        return ("Gmail App Password ("
                "<a href='#' style='color:#1a73e8;text-decoration:underline;' onclick=\"window.parent.postMessage('show_gmail_popup','*')\">see instructions</a>)", True)

    # Custom HTML/JS to trigger Streamlit state change for modal
    components.html('''
    <script>
    window.addEventListener('message', function(event) {
        if (event.data === 'show_gmail_popup') {
            window.parent.streamlitSend({type:'streamlit:setComponentValue', value:true, key:'show_gmail_popup'});
        }
    });
    </script>
    ''', height=0)

    label_html, _ = gmail_label()
    st.markdown(label_html, unsafe_allow_html=True)
    # Removed duplicate Gmail App Password input and Send Emails button here to avoid StreamlitDuplicateElementKey error
    if st.session_state.get('show_gmail_popup', False):
        with st.container():
            st.info("**Gmail App Password Instructions**")
            show_gmail_instructions()
            if st.button("Close Instructions", key="close_gmail_popup"):
                st.session_state['show_gmail_popup'] = False
    # --- End Gmail Credentials Section ---

    # Show Send Emails button after credentials are entered
    if sender_email and app_password:
        send_status = st.empty()
        log_area = st.empty()
        if st.button("Send Emails", key="send_emails_button_results"):
            import smtplib
            from email.mime.text import MIMEText
            import traceback
            successes = []
            failures = []
            logs = []
            try:
                logs.append("Connecting to Gmail SMTP server...")
                log_area.info("\n".join(logs))
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    logs.append(f"Logging in as {sender_email}...")
                    log_area.info("\n".join(logs))
                    server.login(sender_email, app_password)
                    logs.append("Login successful. Sending emails...")
                    log_area.info("\n".join(logs))
                    for idx, row in preview_df.iterrows():
                        recipient = row['Email']
                        subject = row['Email Subject']
                        body = row['Email Body']
                        try:
                            logs.append(f"Sending to {recipient} (subject: {subject})...")
                            log_area.info("\n".join(logs))
                            msg = MIMEText(body, "plain")
                            msg["Subject"] = subject or "Personalized Outreach"
                            msg["From"] = sender_email
                            msg["To"] = recipient
                            server.sendmail(sender_email, recipient, msg.as_string())
                            successes.append(recipient)
                            logs.append(f"✅ Sent to {recipient}")
                        except Exception as e:
                            failures.append((recipient, str(e)))
                            logs.append(f"❌ Failed to send to {recipient}: {e}")
                        log_area.info("\n".join(logs))
                    logs.append("All emails processed.")
                    log_area.info("\n".join(logs))
            except Exception as e:
                logs.append(f"Critical error: {e}\n{traceback.format_exc()}")
                log_area.error("\n".join(logs))
            send_status.success(f"Sent {len(successes)} emails successfully.")
            if failures:
                send_status.error(f"Failed to send to: {', '.join([f[0] for f in failures])}")


        try:
            logs.append("Connecting to Gmail SMTP server...")
            log_area.info("\n".join(logs))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                logs.append("Logging in as {}...".format(sender_email))
                log_area.info("\n".join(logs))
                server.login(sender_email, app_password)
                logs.append("Login successful. Sending emails...")
                log_area.info("\n".join(logs))
                for idx, row in preview_df.iterrows():
                    recipient = row['Email']
                    subject = row['Email Subject']
                    body = row['Email Body']
                    try:
                        logs.append(f"Sending to {recipient} (subject: {subject})...")
                        log_area.info("\n".join(logs))
                        msg = MIMEText(body, "plain")
                        msg["Subject"] = subject or "Personalized Outreach"
                        msg["From"] = sender_email
                        msg["To"] = recipient
                        server.sendmail(sender_email, recipient, msg.as_string())
                        successes.append(recipient)
                        logs.append(f"✅ Sent to {recipient}")
                    except Exception as e:
                        failures.append((recipient, str(e)))
                        logs.append(f"❌ Failed to send to {recipient}: {e}")
                    log_area.info("\n".join(logs))
                logs.append("All emails processed.")
                log_area.info("\n".join(logs))
        except Exception as e:
            logs.append(f"Critical error: {e}\n{traceback.format_exc()}")
            log_area.error("\n".join(logs))
        send_status.success(f"Sent {len(successes)} emails successfully.")
        if failures:
            send_status.error(f"Failed to send to: {', '.join([f[0] for f in failures])}")

    if st.button("Do it Again", key="do_it_again_button"):
        for key in list(st.session_state.keys()):
            if key not in ['course_details', 'persona', 'sender_email', 'app_password', 'user_df']:
                del st.session_state[key]
        st.session_state['results'] = None
        st.rerun()
