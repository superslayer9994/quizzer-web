import streamlit as st
import fitz  # PyMuPDF
import re
import time
import unicodedata
import pandas as pd
import matplotlib.pyplot as plt

# ------------------ Extract MCQs and Answer Key ------------------
def extract_mcqs_and_answers_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    full_text = ""
    for page in doc:
        text = page.get_text()
        text = ''.join(c for c in text if not unicodedata.category(c).startswith('C'))
        full_text += text

    # Extract MCQs
    question_blocks = re.split(r"Q\.(\d+)\.", full_text)
    mcqs = []
    for i in range(1, len(question_blocks), 2):
        q_number = question_blocks[i]
        block = question_blocks[i + 1].strip()
        question_match = re.match(r"(.*?)(\(a\).*?\(b\).*?\(c\).*?\(d\).*?)(?=Q\.|$)", block, re.DOTALL)
        if question_match:
            question_text = question_match.group(1).strip()
            options_block = question_match.group(2)
            options = re.findall(r"\(a\)(.*?)\(b\)(.*?)\(c\)(.*?)\(d\)(.*?)(?=Q\.|$)", options_block, re.DOTALL)
            if options:
                opt = [o.strip().replace('\n', ' ') for o in options[0]]
                mcqs.append((q_number, question_text, opt))

    # Extract answer key
    answer_key = {}
    match = re.search(r"Answer Key\s*[:-]+(.*)", full_text, re.DOTALL | re.IGNORECASE)
    if match:
        answer_block = match.group(1)
        answers = re.findall(r"(\d+)\.\(([a-dA-D])\)", answer_block)
        answer_key = {num: ans.lower() for num, ans in answers}

    return mcqs, answer_key

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="MCQ Quizzer", layout="centered")
st.title("🧠 Live MCQ Quizzer with Analytics")

uploaded_pdf = st.file_uploader("Upload your combined MCQ PDF (with Answer Key)", type=["pdf"])

if uploaded_pdf:
    with st.spinner("Reading your PDF..."):
        mcqs, answer_key = extract_mcqs_and_answers_from_pdf(uploaded_pdf)

    if not mcqs or not answer_key:
        st.error("Could not extract questions or answer key. Please check the PDF format.")
    else:
        st.success(f"Found {len(mcqs)} questions. Proceed to select your range.")

        q_numbers = [int(q[0]) for q in mcqs]
        min_q, max_q = min(q_numbers), max(q_numbers)
        q_start = st.number_input("From Question No:", min_value=min_q, max_value=max_q, value=min_q)
        q_end = st.number_input("To Question No:", min_value=min_q, max_value=max_q, value=min_q + 4)

        if q_start <= q_end:
            selected_mcqs = [q for q in mcqs if int(q[0]) >= q_start and int(q[0]) <= q_end]
            st.markdown("---")
            st.header("📝 Attempt the Quiz")

            responses = []
            times = []

            for idx, (q_no, question, options) in enumerate(selected_mcqs):
                st.subheader(f"Q{q_no}. {question}")
                start_time = time.time()
                response = st.radio("Select your answer:", options, key=f"q_{q_no}", index=None)
                elapsed = round(time.time() - start_time, 2)
                responses.append(response)
                times.append(elapsed)

            if st.button("Submit Quiz"):
                correct, wrong, skipped, total_score = 0, 0, 0, 0
                per_q_result = []

                for i, (q_no, _, options) in enumerate(selected_mcqs):
                    selected = responses[i]
                    correct_ans = answer_key.get(q_no)
                    selected_label = None
                    for label, opt in zip(['a', 'b', 'c', 'd'], options):
                        if opt == selected:
                            selected_label = label
                            break
                    if selected_label is None:
                        skipped += 1
                        result = "Skipped"
                        score = 0
                    elif selected_label == correct_ans:
                        correct += 1
                        result = "Correct"
                        score = 2
                    else:
                        wrong += 1
                        result = "Wrong"
                        score = -0.5
                    total_score += score
                    per_q_result.append((q_no, selected_label if selected_label else "-", correct_ans, result, times[i]))

                st.markdown("---")
                st.header("📊 Quiz Summary")
                st.markdown(f"**Total Questions:** {len(selected_mcqs)}")
                st.markdown(f"**Attempted:** {len(selected_mcqs) - skipped}")
                st.markdown(f"✅ Correct: {correct} | ❌ Wrong: {wrong} | ❓ Skipped: {skipped}")
                st.markdown(f"🎯 Final Score: **{total_score}**")
                st.markdown(f"⏱️ Avg Time/Q: {round(sum(times)/len(times), 2)} sec")

                # Plotting
                df = pd.DataFrame(per_q_result, columns=["Q.No", "Your Ans", "Correct Ans", "Result", "Time (s)"])
                fig, ax = plt.subplots()
                df['Result'].value_counts().plot(kind='pie', autopct='%1.1f%%', startangle=90, ax=ax)
                ax.set_ylabel('')
                st.pyplot(fig)

                st.markdown("---")
                st.subheader("🔍 Question-wise Feedback")
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("Invalid range selection.")
