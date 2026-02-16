import requests
import json
import argparse

class AniLibriaIntegration:
    BASE_URL = 'https://ani.libria.tv/api/'

    def __init__(self, language='en'):
        self.language = language

    def search(self, query):
        response = requests.get(f'{self.BASE_URL}search', params={'query': query, 'lang': self.language})
        return response.json()

    def get_dubbed_anime(self, anime_id):
        response = requests.get(f'{self.BASE_URL}anime/{anime_id}/dubs', params={'lang': self.language})
        return response.json()

def main():
    parser = argparse.ArgumentParser(description='Ani-cli-ru: Anime CLI with AniLibria integration')
    parser.add_argument('query', type=str, help='Search query for anime')
    parser.add_argument('--lang', choices=['ru', 'en'], default='ru', help='Language: Russian (ru) or English (en)')
    args = parser.parse_args()

    ani_lib = AniLibriaIntegration(language=args.lang)
    results = ani_lib.search(args.query)
    print(json.dumps(results, ensure_ascii=False, indent=4))

if __name__ == '__main__':
    main()