from django.http import HttpResponseRedirect
from django.shortcuts import render
from os import getenv
import urllib
import requests

# Create your views here.
def home(request):
    return render(request, 'home/home.html')

def authorize(request):
    if request.method == "POST":
        token = request.POST['token']
        key = getenv('AUTH_KEY')
        if token == key:
            booru_key = getenv("BOORU_KEY")
            request.session['key'] = booru_key
        return HttpResponseRedirect('/booru')
        
def booru(request):
    if request.session.has_key('key'): #Current session is approved
        return render(request, 'booru/booru.html')
    return HttpResponseRedirect("/") #not authorized, redired to login

def search(request):
    #Server will use hydrus comma-delimination instead of space like others. Makes it a bit easier I feel
    if request.session.has_key('key'): #Current session is approved
        tags = request.GET['tags'].split(',')
        for i in range(0, len(tags)):
            tags[i] = "\"" + str.strip(tags[i]) + "\""
        file_ids = getIdsFromHydrus(request, *tags)
        return render(request, 'booru/results.html', {'ids': file_ids, 'total': len(file_ids), 'tags': tags})

def getIdsFromHydrus(request, *tags):
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + "/get_files/search_files?tags="
        tag_string = "["
        for tag in tags:
            print(tag)
            tag_string += tag + ","
        tag_string = tag_string[:-1]
        tag_string += "]"
        url += urllib.parse.quote(tag_string)
        print(url)
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': request.session['key'],
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        ids = res.json()['file_ids']
        return ids

def getThumbnail(request, hydrus_id):
    url = getenv('HYDRUS_BASE') + "/get_files/thumbnail?file_id=" + hydrus_id
    res = requests.get(url, headers={
        'Hydrus-Client-API-Access-Key': request.session['key'],
        'User-Agent': "Pydrus-Client/1.0.0"
    })
    