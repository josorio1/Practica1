from bs4 import BeautifulSoup
import requests
import pandas as pd 


# Creamos una clase general para scrapear Reddit
class RedditScraper():
    
    # Definimos atributos
    def __init__(self, url):
        self.url = url
        self.classes_html = {}


    def html_downloader(self):
        """
        Downloads the HTML from a given URL.
        """
        response = requests.get(self.url, headers={"User-Agent": "Mozilla/5.0"})
        return response
    
    
    def scrape(self):
        html_file = self.html_downloader()
        soup = BeautifulSoup(html_file.text, 'html.parser')
        post_titles = []
        post_bodies = []
        for i,post in enumerate(soup.find_all("div", class_=self.classes_html["post"])):
            title = post.find("h3", class_=self.classes_html["post_title"]) # finds post titles
            body = post.find("p", class_=self.classes_html["post_body"]) # finds post bodies
            
            post_titles.append(title.get_text())
            post_bodies.append(body.get_text() if body is not None else None) #get_text gives error in body is None
            
        #print(post_titles)
        #print(post_bodies)
        
        
        df = pd.DataFrame({"Title": post_titles, "Body": post_bodies})
        #print(df.head())
        return df



# Creamos una clase concreta para WSBets que hereda la clase base de Reddit.
# Probablemente no haga falta
class WSBetsScraper(RedditScraper):
    def __init__(self, url = "https://www.reddit.com/r/wallstreetbets/new/"):
        self.url = url
        self.classes_html = {"post": "Post",
                            "post_title": "_eYtD2XCVieq6emjKBH3m",
                            "post_body": "_1qeIAgB0cPwnLhDF9XSiJM"}