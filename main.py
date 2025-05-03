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

# Store results for later use
if 'results' not in st.session_state:
    st.session_state['results'] = None

st.header("LinkedIn Login Details")
linkedin_email = st.text_input("LinkedIn Email", type="default")
linkedin_password = st.text_input("LinkedIn Password", type="password")

st.header("Gmail Credentials for Sending Emails")
if 'sender_email' not in st.session_state:
    st.session_state['sender_email'] = ''
if 'app_password' not in st.session_state:
    st.session_state['app_password'] = ''
sender_email = st.text_input("Your Gmail Address (sender)", value=st.session_state['sender_email'], key="sender_email_input")
st.session_state['sender_email'] = sender_email
app_password = st.text_input("Gmail App Password (see instructions)", type="password", value=st.session_state['app_password'], key="app_password_input")
st.session_state['app_password'] = app_password

progress_placeholder = st.empty()
error_placeholder = st.empty()

if st.button("Start Workflow"):
    if not st.session_state['course_details'] or not st.session_state['persona'] or st.session_state['user_df'] is None:
        st.error("Please fill in all fields and upload a valid Excel file before starting.")
    elif not linkedin_email or not linkedin_password:
        st.error("Please enter your LinkedIn credentials.")
    elif not sender_email or not app_password:
        st.error("Please enter your Gmail credentials for sending emails.")
    else:
        st.info("Running workflow. This may take a few minutes...")
        workflow = OutreachWorkflow(db_type='supabase', linkedin_email=linkedin_email, linkedin_password=linkedin_password)
        user_df = st.session_state['user_df']
        if user_df.shape[0] == 0:
            st.error("No rows found in the uploaded file.")
        else:
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
            progress_placeholder.empty()
            error_placeholder.empty()

if st.session_state['results'] is not None:
    st.success(f"Generated {len(st.session_state['results'])} personalized emails!")

    def split_subject_body(draft):
        if draft and ("\n" in draft or "\r" in draft):
            first_line, *rest = draft.splitlines()
            return first_line.strip(), "\n".join(rest).strip()
        return draft.strip(), ""

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
    send_status = st.empty()
    log_area = st.empty()
    if st.button("Send Emails", key="send_emails_button"):
        import smtplib
        from email.mime.text import MIMEText
        import traceback
        successes = []
        failures = []
        sender_email = st.session_state.get('sender_email', '')
        app_password = st.session_state.get('app_password', '')
        logs = []
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
        st.session_state['results'] = None
        st.experimental_rerun()
