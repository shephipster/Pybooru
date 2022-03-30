from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from os import getenv
import urllib
import requests

#Inspiration from https://github.com/floogulinc/hyshare/blob/master/src/

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

#/thumbnail/<id>
def thumbnail(request, id):
    return HttpResponse(getThumbnail(request, id))

# /view/<id>
def view(request, id):
    fileData = getMetaDataFromHydrusById(request, id)
    sntstt = fileData['service_names_to_statuses_to_tags']
    mt = sntstt['all known tags']
    tags = mt['0']
    return render(request, 'booru/display.html', {
        'id': id,
        'tags': tags
    })

# /image/<id>
def image(request, id):
    return HttpResponse(getImage(request, id))

def search(request):
    #Server will use hydrus comma-delimination instead of space like others. Makes it a bit easier I feel
    if request.session.has_key('key'): #Current session is approved
        tags = request.GET['tags'].split(',')
        cleaned_tags_string = ""
        for i in range(0, len(tags)):
            cleaned_tags_string += tags[i] + ", "
            tags[i] = "\"" + str.strip(tags[i]) + "\""            
        cleaned_tags_string = cleaned_tags_string[:-2]
        file_ids = getIdsFromHydrus(request, *tags)
        
        #Thumbnails
        thumbnail_urls = []
        for id in file_ids:
            thumbnail_urls.append(getThumbnailUrlFromId(request, id))

        #pagination
        page_num = request.GET.get('page', 1)
        paginator = Paginator(file_ids, 25)
        try:
            page_obj = paginator.page(page_num) #get the apporpriate page
        except PageNotAnInteger:
            page_obj = paginator.page(1)    #Return to page 1 if invalid page
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)  #return to last page if going too far
        
        return render(request, 'booru/results.html', {
            'ids': file_ids, 
            'total': len(file_ids),
            'tags': request.GET['tags'],
            'tagString':cleaned_tags_string,
            'page_obj': page_obj
        })

def tagsToHydrusString(*tags):
    tag_string = "["
    for tag in tags:
        tag_string += tag + ","
    tag_string = tag_string[:-1]
    tag_string = tag_string + ",\"system:archive\"]"
    url = urllib.parse.quote(tag_string)
    return url

def getIdsFromHydrus(request, *tags):
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + "/get_files/search_files?tags="
        url += tagsToHydrusString(*tags)
        print(url)
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': request.session['key'],
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        ids = res.json()['file_ids']
        return ids

def getThumbnail(request, hydrus_id):
    url = getenv('HYDRUS_BASE') + "/get_files/thumbnail?file_id=" + str(hydrus_id)
    res = requests.get(url, headers={
        'Hydrus-Client-API-Access-Key': request.session['key'],
        'User-Agent': "Pydrus-Client/1.0.0"
    })
    return res.content  

def getImage(request, hydrus_id):
    url = getenv('HYDRUS_BASE') + "/get_files/file?file_id=" + str(hydrus_id)
    res = requests.get(url, headers={
        'Hydrus-Client-API-Access-Key': request.session['key'],
        'User-Agent': "Pydrus-Client/1.0.0"
    })
    return res.content  

def getThumbnailUrlFromId(request, id):
    if request.session['key']:
        """ This is absolutely influenced by hyshare """
        return (getenv('HYDRUS_BASE') + 'get_files/thumbnail?id=' + str(id) + '&Hydrus-Client-API-Access-Key=' + request.session['key'])
    return ""

def getFileUrlFromId(request, id):
    if request.session['key']:
        """ This is absolutely influenced by hyshare """
        return (getenv('HYDRUS_BASE') + 'get_files/file?id=' + str(id) + '&Hydrus-Client-API-Access-Key=' + request.session['key'])
    return ""

def getMetaDataFromHydrusById(request, id):
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + '/get_files/file_metadata?file_ids=[' + str(id) + ']'
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': request.session['key'],
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        data = res.json()['metadata'][0]
        return data