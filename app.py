import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup as bs
import time

# Function to load cookies from a Netscape format cookies.txt file
def load_cookies(browser, cookies):
    for line in cookies.splitlines():
        if not line.startswith('#') and line.strip():
            fields = line.strip().split('\t')
            if len(fields) == 7:
                cookie = {
                    'domain': fields[0],
                    'flag': fields[1],
                    'path': fields[2],
                    'secure': fields[3],
                    'expiration': fields[4],
                    'name': fields[5],
                    'value': fields[6]
                }
                browser.add_cookie({
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie['path'],
                    'expiry': int(cookie['expiration']) if cookie['expiration'] else None
                })

# Streamlit app setup
st.title("LinkedIn Scraper UI")
st.write("Upload your LinkedIn cookies file, specify the max number of posts, and provide a profile URL to scrape recent posts data. The app will display the top 20 and bottom 20 posts based on reactions and comments.")

# File upload for cookies.txt
uploaded_file = st.file_uploader("Choose your cookies.txt file", type="txt")

# Text input for LinkedIn profile URL
profile_url = st.text_input("Enter the LinkedIn profile URL (e.g., https://www.linkedin.com/in/username/)")

# Numeric input for max number of posts
max_posts = st.number_input("Enter the maximum number of posts to scrape", min_value=1, max_value=3000, value=100)

# Button to trigger scraping
if st.button("Start Scraping"):
    if uploaded_file is not None and profile_url:
        # Read cookies file content
        cookies = uploaded_file.read().decode("utf-8")

        # Set up Selenium
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        browser = webdriver.Chrome(options=chrome_options)

        # Set window size and navigate to LinkedIn
        browser.set_window_size(1920, 1080)
        browser.get('https://www.linkedin.com/')

        # Load cookies into the browser
        load_cookies(browser, cookies)

        # Refresh the page after applying cookies
        browser.refresh()

        # Wait for the navigation bar to appear
        try:
            WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#global-nav .global-nav__me')))
            st.write("Login successful! Starting scraping...")
        except Exception as e:
            st.error("Error logging in with cookies. Please check your file.")
            browser.quit()
            st.stop()

        # Navigate to the user's recent activity page
        browser.get(profile_url)
        time.sleep(5)

        # Scroll through the page and scrape posts
        posts_data = []
        post_count = 0
        LOAD_PAUSE_TIME = 10

        while post_count < max_posts:
            linkedin_soup = bs(browser.page_source, "html.parser")
            containers = linkedin_soup.find_all("div", {"class": "social-details-social-counts"})

            # Process each post
            for container in containers:
                if post_count >= max_posts:
                    break

                try:
                    post_content_container = container.find_previous("div", {"class": "update-components-text"})
                    post_content = post_content_container.text.strip() if post_content_container else "No content"
                except:
                    post_content = "No content"

                try:
                    post_reactions = container.find("li", {"class": "social-details-social-counts__reactions"}).find("button")["aria-label"].split(" ")[0].replace(',', '')
                except:
                    post_reactions = "0"
                try:
                    post_comments = container.find("li", {"class": "social-details-social-counts__comments"}).find("button")["aria-label"].split(" ")[0].replace(',', '')
                except:
                    post_comments = "0"

                posts_data.append({
                    'Content': post_content,
                    'Reactions': int(post_reactions.replace('K', '000').replace('M', '000000')),
                    'Comments': int(post_comments.replace('K', '000').replace('M', '000000')),
                })

                post_count += 1

            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(LOAD_PAUSE_TIME)

        # Convert scraped data to DataFrame
        df = pd.DataFrame(posts_data)

        # Display top 20 posts by reactions and comments
        st.subheader("Top 20 Posts with Highest Reactions and Comments")
        top_20 = df.nlargest(20, ['Reactions', 'Comments'])
        st.write(top_20)

        # Display bottom 20 posts by reactions and comments
        st.subheader("Bottom 20 Posts with Lowest Reactions and Comments")
        bottom_20 = df.nsmallest(20, ['Reactions', 'Comments'])
        st.write(bottom_20)

        # Save DataFrame to CSV
        csv_file = "scraped_posts.csv"
        df.to_csv(csv_file, index=False)
        st.success(f"Scraping completed! {post_count} posts scraped.")
        
        # Provide download link for the entire dataset (not just top and bottom 20 posts)
        st.download_button(
            label="Download Full Dataset as CSV",
            data=open(csv_file, "rb"),
            file_name="linkedin_posts.csv",
            mime="text/csv"
        )
        
        # Close the browser
        browser.quit()
    else:
        st.warning("Please upload the cookies file and provide a valid LinkedIn profile URL.")

