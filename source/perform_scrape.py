
import sys 
sys.path.append("./")
from source.scraper import WSBetsScraper
import argparse 


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, help="URL para escrapear scrape")
    parser.add_argument("--dest", type=str, help="carpeta donde guardar el dataset")
    parser.add_argument("--n-posts", type=int, help="número de posts")
    parser.add_argument("--comments-per-post", type=int, help="límite de comentarios por post")
    parser.add_argument("--date-limit", type=str, help="fecha límite para coger posts. El formato ha de ser del estilo 'hace 9 días'.")
    
    
    args = parser.parse_args()
    scraper = WSBetsScraper(url=args.url)
    
    user_agent = scraper.driver.execute_script("return navigator.userAgent")
    print("Inicializando script para scrapear WallStreetBets\n")
    print(f"El User Agent que está siendo empleado es: {user_agent}\n")
    
    df = scraper.scrape(n_posts=args.n_posts,
                        comments_per_post=args.comments_per_post,
                        date_limit=args.date_limit
                        )
    df.to_csv("dataset/wsb_dataset.csv", index=False)