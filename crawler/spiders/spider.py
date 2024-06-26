import scrapy
from urllib.parse import urlparse, parse_qs
import re
import os

def normalize_url(url):
    url_norm = url.strip()
    
    if not url_norm.startswith(('http://', 'https://')):
        url_norm = 'https://' + url_norm
    if "https://www." in url_norm:
        return url_norm.replace("https://www.", "https://")
    elif "http://www." in url_norm:
        return url_norm.replace("http://www.", "http://")
    else: 
        return url_norm

SUBDOMAINS = ['ut.ee']
FORBIDDEN_SUBDOMAINS = []

# with open('subdomains.txt', 'r') as f:
#     SUBDOMAINS = [line.strip() for line in f.readlines()]

with open('forbidden_subdomains.txt', 'r') as f:
    FORBIDDEN_SUBDOMAINS = [line.strip() for line in f.readlines()]

class SubdomainUrlChecker:

    def __init__(self, subdomain):
        self.forbidden_subdomains = FORBIDDEN_SUBDOMAINS
        self.subdomain = subdomain 
        self.forbidden_query_params = []
        self.forbidden_paths = []
#       self.visited = VISITED_SITES

    def is_allowed_url(self, abs_url):
        if "mailto:" in abs_url or "tel:" in abs_url:
            return False
        
        parsed_url = urlparse(abs_url)
        netloc = parsed_url.netloc
        path = parsed_url.path
        query = parsed_url.query

#       if self.is_visited_site(abs_url): #For courses.cs.ut.ee or when required to scrape already scraped urls
#           return False
        if self.contains_forbidden_subdomains(netloc):
            return False
        if self.contains_forbidden_path(path):
            return False
        if self.contains_forbidden_query(query): # if any of the forbidden query params are present
            return False
        if not ("ut.ee" in abs_url or self.subdomain in abs_url):
            return False

        return True

    """
    def is_visited_site(self, site):
        for visited_site in self.visited:
            if site == visited_site:
                return True
        return False
    """

    def contains_forbidden_path(self, path):
        for forbidden_path in self.forbidden_paths:
            if forbidden_path in path:
                return True

    def contains_forbidden_subdomains(self, domain):
        for forbidden_subdomain in self.forbidden_subdomains:
            if forbidden_subdomain in domain:
                return True

    def contains_forbidden_query(self, query):
        query_params = parse_qs(query)

        if not query_params:
            if query: # check for no key-value pair query parameter
                print("NO KEY-VALUE PARAM: ", query_params)

                regex = "(http|https):\/\/.*"
                if re.match(regex, query):
                    return True
        else:
            print("PARAMS: ", query_params)
            for forbidden_query_param in self.forbidden_query_params:
                if forbidden_query_param in query_params.keys():
                    return True
            
            regex = "(http|https):\/\/.*"
            for key in query_params.keys():
                if re.match(regex, key):
                    return True

        return False

class QuotesSpider(scrapy.Spider):
    name = "subdomains"

    def start_requests(self):
        subdomains = SUBDOMAINS
        print("SUBDOMAINS", subdomains)
        
        subdomain_max_depth= {
            "courses.cs.ut.ee": 2,
        }

        for subdomain in subdomains:
            url = normalize_url(subdomain)
            url_checker = SubdomainUrlChecker(subdomain)
            folder_name = subdomain.replace('.', '_')
            folder_path = f"links/{folder_name}"
            max_depth = subdomain_max_depth[subdomain] if subdomain_max_depth.get(subdomain) else 1

            yield scrapy.Request(url=normalize_url(subdomain), 
                                     callback=self.parse, 
                                     cb_kwargs={'folder_path': folder_path, 
                                                "url_checker": url_checker,
                                                "depth": 0, 
                                                "max_depth": max_depth})

    def download_url(self): # modify function here
        # url = response.url.split("/")[-2] 
        # filename = f"ut-{url}.html"
        # Path(filename).write_bytes(response.body)
        pass

    def parse(self, response, folder_path, url_checker, depth, max_depth):
        abs_url = response.url

        if not url_checker.is_allowed_url(abs_url): 
            print("FORBIDDEN LINK: ", abs_url)

            with open(f"{folder_path}/forbidden_links.txt", 'a') as file:
                file.write(abs_url + '\n')
            return  

        print("ALLOWED LINK: ", abs_url, "DEPTH:", depth)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        with open(f"{folder_path}\links.txt", 'a') as file:
            file.write(abs_url + '\n')

        links = response.css("a::attr(href)").getall()
        
        if depth < max_depth:
            for link in links:
                if link is not None:
                    abs_url = response.urljoin(link)

                if not url_checker.is_allowed_url(abs_url): 
                    print("FORBIDDEN LINK: ", abs_url)

                    with open(f"{folder_path}/forbidden_links.txt", 'a') as file:
                        file.write(abs_url + '\n')
                    continue     
                
                yield scrapy.Request(url=abs_url, 
                                     callback=self.parse, 
                                     cb_kwargs={'folder_path': folder_path, 
                                                "url_checker": url_checker,
                                                "depth": depth+1, 
                                                "max_depth": max_depth })
