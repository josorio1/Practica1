
import sys 
sys.path.append("./")
from source.scraper import WSBetsScraper
import argparse 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of the program")
    parser.add_argument("--url", type=str, help="URL to scrape")
    parser.add_argument("--dest", type=str, help="dataset destination")
    
    
    args = parser.parse_args()
    
    scraper = WSBetsScraper(url=args.url)
    df = scraper.scrape()
    df.to_csv("dataset/wsb_dataset.csv", index=False)