from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd 
import time
import numpy as np
import re 
from datetime import datetime, timedelta


class RedditScraper():
    
    def __init__(self, url):
        self.url = url
        self.base_url = re.search(r"^https?:\/\/(?:.*?\.)?([^\/]+\.com)", self.url).group(0)
        self.classes_html = {}
        self.driver = None
            
    def date_calculator(self, reddit_time):
        """
        Calcula la fecha en la que se ha publicado un post/comentario de reddit. Las fechas son calculadas en función de la precisión proporcionada por Reddit.
        Por ejemplo, si una fecha es "hace 9 minutos", la fecha calculada tendrá precisión de minutos.
        
        Parámetros
        ----------
        reddit_time: str
                Cadena de caracteres del tipo "hace 8 minutos".
                
        Devuelve
        --------
        prev_date: datetime
                Fecha de publicación del post o comentario 
        """
        
        now = datetime.now()
        time_split = reddit_time.split(" ")
        try:
            if time_split[2] in ["segundo","segundos", "s"]:
                prev_date = now - timedelta(seconds=int(time_split[1]))
                prev_date = prev_date.strftime("%Y-%m-%d %H:%M:%S")
            elif time_split[2] in ["minuto", "minutos", "min"]:
                prev_date = now - timedelta(minutes=int(time_split[1]))
                prev_date = prev_date.strftime("%Y-%m-%d %H:%M")
            elif time_split[2] in ["hora", "horas", "h"]:
                prev_date = now - timedelta(hours=int(time_split[1])) 
                prev_date = prev_date.strftime("%Y-%m-%d %H")
            elif time_split[2] in ["día", "días", "d"]:
                prev_date = now - timedelta(days=int(time_split[1]))
                prev_date = prev_date.strftime("%Y-%m-%d") 
        except:
            prev_date = None
        
        return prev_date
              
    def selenium_heuristic_computator(self, n_scrolls=5):
        """
        Computa la media y desviación estándar de posts por scroll.
        
        Parámetros
        ----------  
        n_scrolls: int, default = 5
                Límite de scrolls. 
                
        Devuelve
        -------
        np.mean(posts_per_scroll): float
                Media de posts por scroll.
                  
        np.std(posts_per_scroll): float 
                Desviación estándar de los posts por scroll.
        """
     
        count_posts = 0
        count_posts_aux = 0
        posts_per_scroll = []
        i = 0 
        print(f"Computando heurística a partir de {n_scrolls} scrolls...\n")
        while i < n_scrolls:
            # Scroll hasta el final de la página
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Parseo del HTML de la página
            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            # Cálculo del número de posts en la página actual
            count_posts = len(soup.find_all("div", class_=self.classes_html["post"]))   
            time.sleep(2)
            
            if count_posts_aux == count_posts: # Asume que no vamos a llegar al final absoluto del foro
                print("Repitiendo scroll porque la espera no fue suficiente", {i})
            else: 
                i+= 1
                posts_per_scroll.append(count_posts - count_posts_aux)
                count_posts_aux = count_posts

                            
        return np.mean(posts_per_scroll), np.std(posts_per_scroll)
              
    def selenium_scroller(self, n_posts, n_scrolls):
        """
        Scroll de una página infinita hasta el número indicado de posts.
        La función necesita un número de scrolls determinados para comenzar a funcionar.
        Es posible calcular un valor a través de métodos heurísticos, como por ejemplo
        el devuelto por la funcion selenium_heuristic_computator.
        
        Parámetros
        ---------
        n_scrolls: int
            Número de scrolls a realizar.
             
        post_limit: int
            Número de posts a conseguir.
            
        Devuelve
        --------
        soup: object
            Página HTML parseada
        """
                     
        # Empezar scroll    
        count_posts = 0 
        count_posts_aux = 0
        print(f"Comenzando scraping de {n_posts} posts...\n")
        while count_posts < n_posts:
            for j in range(n_scrolls):
                # Scroll hasta el fondo de la página
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")                        
                time.sleep(2)
            
            # Parsear la página HTML generado
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            # Calcular el número de posts en la página 
            count_posts = len(soup.find_all("div", class_=self.classes_html["post"]))
            print("Número de posts escrapeados: ", count_posts)
            # Actualización del número de scrolls necesarios basándose en el número de posts que faltan
            if count_posts < n_posts:
                frac_missing_posts = n_posts / count_posts 
                n_scrolls = int((frac_missing_posts -1) * n_scrolls) + 1 
                print(f"Número de posts insuficiente. Se realizarán {n_scrolls} scrolls extra.")
            
    
        return soup
 
    def scrape_posts(self, soup, n_posts, date_limit):
        """
        Dado un contenido HTML obtenido con Beautiful Soup, scrapea los siguientes valores de los comentarios:
            - Usuario, fecha de publicación, votos, título y texto y link a los comentarios.
            
        Parámetros
        ----------
        
        soup: bs4.BeautifulSoup
                Contenido HTML parseado.
                
        n_post: int
                Número de posts a scrapear en la página HTML. Se asume que
                anteriormente se ha verificado que hay como mínimo este número
                de posts en el HTML scrapeado.
                
        date_limit: str
                Fecha límite en formato Reddit. Por ejemplo: 'hace 9 días', 'hace 2 horas'. Admite 
                segundos, horas, minutos y días.
                
        Devuelve
        --------
        df - pd.DataFrame
                DataFrame con las siguientes columnas: ["ID_padre","Usuario", "Fecha", "Votos", "Titulo", "Texto", "Link comentario"]
                ID_padre se genera como "-1" por defecto.
        """
        
        date_limit = self.date_calculator(date_limit) # fecha límite en formato datetime
        
        # Scraping de posts       
        columnas = ["ID_padre","Usuario", "Fecha", "Votos", "Titulo", "Texto", "Link comentario"]
        post_parent_ids = []
        post_titles = []
        post_texts = []
        post_usernames = []
        post_dates = []
        post_votes = []
        post_comment_links = []
        
        for i,post in enumerate(soup.find_all("div", class_=self.classes_html["post"])):
            if i == n_posts: # evita coger más posts de los necesarios con el último scroll
                break    
            
            # Si el post es un ad, lo evitamos
            if  post.find("span", class_=self.classes_html["post_ad"]):
                continue
            
            # Scrap de fecha
            date = post.find("span", {"data-testid": "post_timestamp"})
            post_date = self.date_calculator(date.text) if date is not None else -1 
            if post_date != -1: 
                if date_limit > post_date: # Si la fecha del post supera la fecha límite, se rompe loop
                    print(f"La fecha límite para scrapear posts se ha pasado al llegar al post {i}.")
                    break
                else:
                    post_dates.append(post_date)
            
            #Scrap de título
            title = post.find("h3", class_=self.classes_html["post_title"]) 
            post_titles.append(title.get_text() if title is not None else None)
            
            #Scrap de cuerpo de texto
            text = post.find_all("p", class_=self.classes_html["post_body"]) 
            text = " ".join(txt.get_text() for txt in text) if text is not None else None
            post_texts.append(text) 
            
            # Scrap de nombre usuario
            username = post.find("a", class_=self.classes_html["post_username"])["href"]
            post_usernames.append(username.split("/")[2])
                
            # Scrap de votos de post
            vote = post.find("div", class_=self.classes_html["post_vote"])
            post_votes.append(vote.text if vote is not None else None)
            
            # Scrap de link de comentario
            comment = post.find("a", class_=self.classes_html["post_comment"]) # finds post comments
            post_comment_links.append(self.base_url + comment['href'])
            
            post_parent_ids.append(-1) # asignamos -1 para los posts
              
        # Generación de dataframe de posts
        df = pd.DataFrame(dict(zip(columnas,[post_parent_ids, 
                                                   post_usernames, 
                                                   post_dates, 
                                                   post_votes,
                                                   post_titles,
                                                   post_texts,
                                                   post_comment_links])))
        
        
        return df
    
 
    def scrape_comments(self, links, comments_per_post): 
        """
        Dada una lista de URLS de comentarios, realiza el siguiente scraping:
            - Usuario, fecha de publicación, votos y texto y link a los comentarios.
            
        Parámetros
        ----------
    
        n_post: int
                Número de posts a scrapear en la página HTML. Se asume que
                anteriormente se ha verificado que hay como mínimo este número
                de posts en el HTML scrapeado.
                
        comments_per_posts: int
                Límite de comentarios por posts que se escrapean.

        Devuelve
        --------
        df - pd.DataFrame
                DataFrame con las siguientes columnas: ["ID_padre","Usuario", "Fecha", "Votos", "Titulo", "Texto"]
                "Título" se genera como "-1" por defecto.
                Para "ID_padre", se asume que previamente se ha creado un dataframe con scrape_posts
                donde el link "i" pasado en el parámetro link está asociado con la fila "i" de de ese dataframe                 
        """       
        # Abrir URL para comentarios en pestaña secundaria. 
        # Realmente no es necesario, se podría hacer en una única pestaña.
        self.driver.execute_script(f"window.open('{links[0]}');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
   
        # Scrap de comentarios de cada link
        columnas = ["ID_padre","Usuario", "Fecha", "Votos", "Titulo", "Texto"]
        comment_parent_ids = []
        comment_titles = []
        comment_texts = []  
        comment_usernames = []
        comment_dates = []
        comment_votes = []
        
        for i,link in enumerate(links):
            self.driver.get(link)
            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Coger comentarios de cada link
            j = 0
            for comment in soup.find_all("div", class_=self.classes_html["comment"]):
                # Scrap de nombre usuario
                username = comment.find("a", class_=self.classes_html["comment_username"])
                # Se evitan comentarios sin usuario (habitualmente comentarios eliminados)
                if username:
                    # Se evitan comentarios de bots
                    if username["href"].split("/")[2] == "AutoModerator" or username["href"].split("/")[2] == "VisualMod":
                        continue
                    else:                      
                        comment_usernames.append(username["href"].split("/")[2])
                    
                    # Scrap de cuerpo de texto
                    body = comment.find_all("p", class_=self.classes_html["comment_body"]) 
                    comment_texts.append(" ".join(txt.get_text() for txt in body) if body is not None else None)
                
                    # Scrap de fecha
                    date = comment.find("a", {"data-testid": "comment_timestamp"})
                    comment_date = self.date_calculator(date.text) if date is not None else -1
                    comment_dates.append(comment_date)
                                
                    # Scrap de votos 
                    vote = comment.find("div", class_=self.classes_html["comment_vote"])
                    comment_votes.append(vote.text if vote is not None else None)
                    
                    #ID_padre y título
                    comment_parent_ids.append(i+1) # id start with 1
                    comment_titles.append(-1)
                    
                # Romper loop si se llega a límite de comentarios 
                j += 1 
                if j == comments_per_post:
                    break
                
        # Generación de dataframe
        df = pd.DataFrame(dict(zip(columnas,[comment_parent_ids,
                                             comment_usernames,
                                             comment_dates,
                                             comment_votes,
                                             comment_titles,
                                             comment_texts])))
    
    
        return df
        
    def scrape(self, n_posts, comments_per_post, date_limit):
        """
        Scraping completo de posts + comentarios 
        
        Parámetros
        ----------
        
        n_posts: int
                Número de posts que se desean scrapear.
                
        comments_per_posts: int
                Límite de comentarios por posts que se escrapean.
                
        date_limit: str
                Fecha límite en formato Reddit. Por ejemplo: 'hace 9 días', 'hace 2 horas'. Admite 
                segundos, horas, minutos y días.
        """
        
        self.driver.get(self.url)
        
        start = time.time()
        
        # Computación número de scroll estimados
        mean_posts, std_posts = self.selenium_heuristic_computator()
        n_scrolls = int(n_posts / (mean_posts))
        print("Número de scrolls estimados:", n_scrolls)
        soup = self.selenium_scroller(n_scrolls=n_scrolls, n_posts=n_posts) 
        
        # Scrap de posts 
        df_posts = self.scrape_posts(soup=soup, n_posts=n_posts, date_limit=date_limit)   
            
        # Scrap de comentarios
        df_comments = self.scrape_comments(df_posts["Link comentario"].tolist(), comments_per_post=comments_per_post)
        df_posts = df_posts.drop("Link comentario", axis=1)
        
        # Concantenación de dataframes
        df = pd.concat([df_posts, df_comments])
        df.insert(0, 'id', range(1,len(df)+1))
        # Close the driver
        self.driver.quit()
        
        end = time.time()
        print("Tiempo necesario para realizar el scraping: ", end - start)
        
        
        return df
            
            
        
# Creamos una clase concreta para WSBets que hereda la clase base de Reddit.
class WSBetsScraper(RedditScraper):
    def __init__(self, url = "https://www.reddit.com/r/wallstreetbets/new/"):    
        self.url = url
        self.base_url = re.search(r"^https?:\/\/(?:.*?\.)?([^\/]+\.com)", self.url).group(0)
        self.classes_html = {"post": "Post",
                            "post_title": "_eYtD2XCVieq6emjKBH3m",
                            "post_body": "_1qeIAgB0cPwnLhDF9XSiJM",
                            "post_username": "_2tbHP6ZydRpjI44J3syuqC _23wugcdiaj44hdfugIAlnX oQctV4n0yUb0uiHDdGnmE",
                            "post_comment": "_1UoeAeSRhOKSNdY_h3iS1O _1Hw7tY9pMr-T1F4P1C-xNU _3U_7i38RDPV5eBv7m4M-9J _2qww3J5KKzsD7e5DO0BvvU",
                            "post_ad": "_2oEYZXchPfHwcf9mTMGMg8 V0WjfoF5BV7_qbExmbmeR",
                            "post_vote": "_1rZYMD_4xY3gRcSS3p8ODO _3a2ZHWaih05DgAOtvu6cIo",
                            "comment": "Comment",
                            "comment_body": "_1qeIAgB0cPwnLhDF9XSiJM",
                            "comment_username": "wM6scouPXXsFDSZmZPHRo DjcdNGtVXPcxG0yiFXIoZ _23wugcdiaj44hdfugIAlnX",
                            "comment_vote": "_1rZYMD_4xY3gRcSS3p8ODO _25IkBM0rRUqWX5ZojEMAFQ _3ChHiOyYyUkpZ_Nm3ZyM2M"
                            }
         # Inicialización driver
        chrome_options = webdriver.ChromeOptions()
        #chrome_options.add_argument('headless') # Descomentar en caso de que se quiera realizar navegación sin abrir pantalla
        chrome_options.add_argument('--blink-settings=imagesEnabled=false') # no cargamos imágenes 
        self.driver =  webdriver.Chrome(chrome_options=chrome_options)
        