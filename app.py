import streamlit as st
import nltk
import language_tool_python
from transformers import BartForConditionalGeneration, BartTokenizer
from crewai import Agent
from tools import tool
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Load environment variables for article writing
load_dotenv()

# Initialize the LLM with the Google API key
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    verbose=True,
    temperature=0.5,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Load the BART model and tokenizer for summarization
summarization_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
summarization_tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")

# Download NLTK resources
nltk.download('punkt')
from nltk.util import ngrams
from nltk.lm.preprocessing import pad_sequence, padded_everygram_pipeline
from nltk.lm import MLE, Vocabulary
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
import string


def preprocess_text(text):
    tokens = nltk.word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words and token not in string.punctuation]
    return tokens


def plot_most_common_words(text):
    tokens = preprocess_text(text)
    word_freq = nltk.FreqDist(tokens)
    most_common_words = word_freq.most_common(10)

    words, counts = zip(*most_common_words)

    plt.figure(figsize=(10, 6))
    plt.bar(words, counts)
    plt.xlabel('Words')
    plt.ylabel('Frequency')
    plt.title('Most Common Words')
    plt.xticks(rotation=45)
    st.pyplot(plt)


def plot_repeated_words(text):
    tokens = preprocess_text(text)
    word_freq = nltk.FreqDist(tokens)
    repeated_words = [word for word, count in word_freq.items() if count > 1][:10]

    words, counts = zip(*[(word, word_freq[word]) for word in repeated_words])

    plt.figure(figsize=(10, 6))
    plt.bar(words, counts)
    plt.xlabel('Words')
    plt.ylabel('Frequency')
    plt.title('Repeated Words')
    plt.xticks(rotation=45)
    st.pyplot(plt)


def calculate_perplexity(text, model):
    tokens = preprocess_text(text)
    padded_tokens = ['<s>'] + tokens + ['</s>']
    ngrams_sequence = list(ngrams(padded_tokens, model.order))
    perplexity = model.perplexity(ngrams_sequence)
    return perplexity


def calculate_burstiness(text):
    tokens = preprocess_text(text)
    word_freq = nltk.FreqDist(tokens)

    avg_freq = sum(word_freq.values()) / len(word_freq)
    variance = sum((freq - avg_freq) ** 2 for freq in word_freq.values()) / len(word_freq)

    burstiness_score = variance / (avg_freq ** 2)
    return burstiness_score


def is_generated_text(perplexity, burstiness_score):
    if perplexity < 100 and burstiness_score < 1:
        return "Likely generated by a language model"
    else:
        return "Not likely generated by a language model"


# Grammar Checking Function with explanations
def check_grammar_with_explanations(text):
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(text)
    errors = []

    for match in matches:
        errors.append({
            'error': match.message,
            'incorrect_text': text[match.offset: match.offset + match.errorLength],
            'suggestions': match.replacements,
            'context': match.context
        })
    return errors


# Text Summarization Function
def summarize_text(input_text):
    inputs = summarization_tokenizer.encode("summarize: " + input_text, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = summarization_model.generate(inputs, max_length=150, num_beams=4, early_stopping=True)
    summary = summarization_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary


# Initialize the Writer agent for article writing
article_writer = Agent(
    role='Writer',
    goal='Narrate compelling tech stories about {topic}',
    verbose=True,
    memory=True,
    backstory=(
        "With a flair for simplifying complex topics, you craft "
        "engaging narratives that captivate and educate, bringing new "
        "discoveries to light in an accessible manner."
    ),
    tools=[tool],
    llm=llm,
    allow_delegation=False
)


# Streamlit App Logic
def main():
    st.title("Your Writing Assistant")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    option = st.sidebar.selectbox("Select Feature", ["Text Analysis", "Grammar Check", "Paraphrasing", "Plagiarism Check", "Text Summarization", "Article Writer"])
    
    if option == "Text Analysis":
        text = st.text_area("Enter the text you want to analyze", height=200)
        if st.button("Analyze"):
            if text:
                # Load or train your language model
                tokens = nltk.corpus.brown.words()  # You can use any corpus of your choice
                train_data, padded_vocab = padded_everygram_pipeline(1, tokens)
                model = MLE(1)
                model.fit(train_data, padded_vocab)

                # Calculate perplexity
                perplexity = calculate_perplexity(text, model)
                st.write("Perplexity:", perplexity)

                # Calculate burstiness score
                burstiness_score = calculate_burstiness(text)
                st.write("Burstiness Score:", burstiness_score)

                # Check if text is likely generated by a language model
                generated_cue = is_generated_text(perplexity, burstiness_score)
                st.write("Text Analysis Result:", generated_cue)

                # Plot most common words
                plot_most_common_words(text)

                # Plot repeated words
                plot_repeated_words(text)

            else:
                st.warning("Please enter some text to analyze.")

    elif option == "Grammar Check":
        text = st.text_area("Enter text for grammar check:", "")
        if st.button("Check Grammar"):
            grammar_errors = check_grammar_with_explanations(text)
            if grammar_errors:
                st.write("Grammar Mistakes Found:")
                for error in grammar_errors:
                    st.write(f"**Error:** {error['error']}")
                    st.write(f"**Incorrect Text:** {error['incorrect_text']}")
                    st.write(f"**Suggestions:** {', '.join(error['suggestions'])}")
                    st.write(f"**Context:** {error['context']}")
            else:
                st.write("No grammar issues detected.")

    elif option == "Text Summarization":
        text = st.text_area("Enter text to summarize:", "")
        if st.button("Summarize"):
            if text:
                summary = summarize_text(text)
                st.write("### Summary:")
                st.write(summary)
            else:
                st.warning("Please enter some text to summarize.")

    elif option == "Article Writer":
        topic = st.text_input("Enter the topic you want to explore:", "")
        if st.button("Write Article"):
            if topic:
                # Generate the article
                result = article_writer.llm.predict(f"Write a compelling tech story about {topic}")
                
                st.write("### Article:")
                st.write(result)

                # Prepare Markdown content for download
                md_content = f"# {topic}\n\n{result}"
                
                # Download button
                st.download_button(
                    label="Download Article as .md",
                    data=md_content,
                    file_name=f"{topic.replace(' ', '_')}.md",
                    mime="text/markdown"
                )
            else:
                st.error("Please enter a topic to explore.")

    # Implement other features like paraphrasing and plagiarism check here

if __name__ == "__main__":
    main()
