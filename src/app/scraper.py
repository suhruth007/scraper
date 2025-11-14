from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from tenacity import retry, stop_after_attempt, wait_exponential
import time
import logging

LOG = logging.getLogger(__name__)

def make_headless_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # user-agent rotation, proxies etc could be added
    driver = webdriver.Chrome(options=options)
    return driver

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def scrape_naukri(query, location, max_pages=1):
    """
    Scrape jobs from Naukri.com
    Returns mock data for testing without Selenium setup
    """
    LOG.info("Scraping %s jobs in %s", query, location)
    
    # For testing without Chrome/Selenium, return mock jobs
    # In production, uncomment the Selenium code below
    mock_jobs = [
        {
            "id": 1,
            "title": "Senior Backend Engineer",
            "company": "TechCorp India",
            "location": location,
            "description": "Looking for experienced backend engineer with Python and Django expertise. 5+ years required.",
            "salary": "15-20 LPA",
            "job_type": "Full-time",
            "url": "https://www.naukri.com/job-1",
            "posted": "2 days ago",
            "experience": "5-7"
        },
        {
            "id": 2,
            "title": "Full Stack Developer",
            "company": "StartupXYZ",
            "location": location,
            "description": "Join our growing team. Experience with React, Node.js, and PostgreSQL needed.",
            "salary": "12-16 LPA",
            "job_type": "Full-time",
            "url": "https://www.naukri.com/job-2",
            "posted": "1 day ago",
            "experience": "3-5"
        },
        {
            "id": 3,
            "title": "DevOps Engineer",
            "company": "CloudServices Ltd",
            "location": location,
            "description": "AWS, Docker, Kubernetes expertise. CI/CD pipeline management.",
            "salary": "13-18 LPA",
            "job_type": "Full-time",
            "url": "https://www.naukri.com/job-3",
            "posted": "3 days ago",
            "experience": "4-6"
        },
        {
            "id": 4,
            "title": "Data Engineer",
            "company": "Analytics Pro",
            "location": location,
            "description": "Build data pipelines. Python, Spark, and SQL expertise required.",
            "salary": "14-19 LPA",
            "job_type": "Full-time",
            "url": "https://www.naukri.com/job-4",
            "posted": "4 days ago",
            "experience": "3-5"
        },
        {
            "id": 5,
            "title": "Machine Learning Engineer",
            "company": "AI Innovations",
            "location": location,
            "description": "Work on cutting-edge ML projects. Experience with TensorFlow and PyTorch.",
            "salary": "16-22 LPA",
            "job_type": "Full-time",
            "url": "https://www.naukri.com/job-5",
            "posted": "5 days ago",
            "experience": "2-4"
        }
    ]
    
    LOG.info("Returning %d mock jobs for testing", len(mock_jobs))
    return mock_jobs
    
    # Uncomment below for real Selenium scraping (requires Chrome/Chromedriver)
    # driver = make_headless_driver()
    # try:
    #     url = f"https://www.naukri.com/{query}-jobs-in-{location}"
    #     LOG.info("Visiting %s", url)
    #     driver.get(url)
    #     time.sleep(2)
    #     jobs = []
    #     cards = driver.find_elements(By.CSS_SELECTOR, "article")
    #     for c in cards[:30]:
    #         title = c.text.split('\n')[0]
    #         jobs.append({"title": title, "source": "naukri"})
    #     return jobs
    # finally:
    #     driver.quit()

# Add other scrapers (indeed, linkedin, glassdoor, remoteok) similar patterns, respecting robots.txt
