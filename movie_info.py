import re
import requests
import urllib
import json

BASE_URL = 'http://www.imdbapi.com/?'
#NAME_LIST = file('movies.txt','r')

def get_movie_info(movi_name):
    query = {'i': '', 't': movi_name ,'tomatoes':'true'}
    part = urllib.urlencode(query)
    url = BASE_URL+part
    response = requests.get(url)
    output  = json.dumps(response.content, separators=(',',':'))
    movie_info = {}
    info_list = ['Plot','Title','Director','tomatoRating', 'imdbRating', 'Runtime']
    for info in info_list:
        if info == 'imdbRating':
            movie_info['IMDB Rating'] = get_and_clean_data(info, output)
        movie_info[info] = get_and_clean_data(info, output)
    return movie_info

def get_and_clean_data(tag, data):
    try:
        temp_data = data.split(tag)[1].split(",")[0]
        data = re.sub(r':\\"+','',temp_data).replace('\\"','')
    except IndexError,e:
        print "Error Occured! %s" %e
        return ""	
    return data	

#def get_movi_name(name_list):
#    for name in name_list:
#        print "Getting Movi %s " % name
#        print get_movie_info(name)
#    return
