from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from os import getenv
import urllib
import requests

#PAGE_SIZES = 30 #how many items to show per page

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

def image(request, id):
    return HttpResponse(getImage(request, id))

# /view/<id>
def view(request, id):
    fileData = getMetaDataFromHydrusById(request, id)
    tags, title = cleanTags(*fileData['service_names_to_statuses_to_tags']['all known tags']['0'])
    urls = fileData['known_urls']
    file_type = getFileType(fileData['mime'])
    height = 0
    width = 0
    if fileData['height']:
        height = fileData['height']
    if fileData['width']:
        width = fileData['width']
    return render(request, 'booru/display.html', {
        'id': id,
        'tags': tags,
        'urls': urls,
        'type': file_type,
        'mime': fileData['mime'],
        'height': height,
        'width': width,
        'title': title
    })
    
# view/full/<id>
def fullImage(request, id):
    fileData = getMetaDataFromHydrusById(request, id)
    file_type = getFileType(fileData['mime'])
    tags, title = cleanTags(*fileData['service_names_to_statuses_to_tags']['all known tags']['0'])
    height = 0
    width = 0
    if fileData['height']:
        height = fileData['height']
    if fileData['width']:
        width = fileData['width']
    return render(request, 'booru/image-only.html', {
        'id': id,
        'fileType': file_type,
        'mime': fileData['mime'],
        'height': height,
        'width': width,
        'title': title
    })

def search(request):
    #Server will use hydrus comma-delimination instead of space like others. Makes it a bit easier I feel
    if request.session.has_key('key'): #Current session is approved
        raw_tags = request.GET['tags']
        tags = raw_tags.split(',')
        title = ""
        
        #Get the page we are working with and only get make request for those files
        page_num = int(request.GET.get('page', 1))
        PAGE_SIZES = int(request.GET.get('page_size', 25))
        page_start = (page_num - 1) * PAGE_SIZES
        page_end = (page_num * PAGE_SIZES)
        
        cleaned_tags_string = ""
        for i in range(0, len(tags)):
            cleaned_tags_string += tags[i] + ", " 
            title += tags[i].upper() + ", "
            tags[i] = "\"" + str.strip(tags[i]) + "\"" 
                       
        cleaned_tags_string = cleaned_tags_string[:-2]
        title = title[:-2]
        
        file_ids = getIdsFromHydrus(request, *tags)
        file_data = []
        
        # Figuring out what is okay and what is not

        for id in file_ids[page_start:page_end]:  
            meta = getMetaDataFromHydrusById(request, id)
            file_data.append(
                {
                    'id': id,
                    'isVideo': isAnimated(meta['mime']),
                    'hasAudio': meta['has_audio']
                })


        #pagination        
        paginator = Paginator(file_ids, PAGE_SIZES)
        try:
            page_obj = paginator.page(page_num) #get the apporpriate page
        except PageNotAnInteger:
            page_obj = paginator.page(1)    #Return to page 1 if invalid page
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)  #return to last page if going too far
        
        return render(request, 'booru/results.html', {
            'data': file_data,
            'tag_string': cleaned_tags_string,
            'tags': raw_tags,
            'page_obj': page_obj,
            'page' : 1,
            'title': title,
            'total' : len(file_ids),
            'page_size': PAGE_SIZES
        })

def isAnimated(mimeType:str):
    switcher = {
        "image/jpeg": False,
        "image/jpg": False,
        "image/png": False,
        "image/apng": True,
        "image/gif": True,
        "image/bmp": False,
        "image/webp":False,
        
        "video/webm": True,
        "video/mp4": True,
        "video/x-matroska": True,
        "video/quicktime": True,
        
        "audio/mp3": False,
        "audio/ogg": False,
        "audio/flac": False,
        "audio/x-wav": False,
        
        "video/x-flv": True,
        "application/x-shockwave-flash": True,
        
        "application/pdf": True
    }
    
    return switcher.get(mimeType, "Invalide Mime Type Submited")

def getFileType(mimeType:str):
    """ 
    0 = <img> Image
    1 = <video> Video
    2 = <audio> Audio
    3 = <embed> Flash
    4 = <embed> PDF
    99 = unsupported
    """
    switcher = {
        "image/jpeg": 0,
        "image/jpg": 0,
        "image/png": 0,
        "image/apng": 0,
        "image/gif": 0,
        "image/bmp": 0,
        "image/webp":0,
        
        "video/webm": 1,
        "video/mp4": 1,
        "video/x-matroska": 1,
        "video/quicktime": 1,
        
        "audio/mp3": 2,
        "audio/ogg": 2,
        "audio/flac": 2,
        "audio/x-wav": 2,
        
        "video/x-flv": 3,
        "application/x-shockwave-flash": 3,
        
        "application/pdf": 4
    }
    return switcher.get(mimeType, 99)

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
        return (getenv('HYDRUS_BASE') + '/get_files/file?file_id=' + str(id) + '&Hydrus-Client-API-Access-Key=' + request.session['key'])
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
    
def cleanTags(*tags):
    """ Take a list of tags and remove certain ones that aren't important for the booru.
    Namely, removes meta:* , booru:*, filename:*, and source:* """
    cleanTags = []
    title = "Shepbooru"
    for tag in tags:
        if not tag.startswith(('booru:', 'filename:', 'meta:', 'source:', 'pixiv work')):
            cleanTags.append(tag)
        if tag.startswith('title:'):
            title = tag[6:]
    return cleanTags, title