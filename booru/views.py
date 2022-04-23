from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from os import getenv
from .forms import *
from .models import *
import urllib
import requests


HYDRUS_AUTH_KEY = getenv('HYDRUS_KEY')
FULL_BOORU_KEY = getenv('FULL_BOORU_KEY')
HYDRUS_BASE = getenv('HYDRUS_BASE')
#PAGE_SIZES = 30 #how many items to show per page

#Inspiration from https://github.com/floogulinc/hyshare/blob/master/src/

# Create your views here.
def home(request):
    return render(request, 'home/home.html')

def authorize(request):
    if request.method == "POST":
        booru_key = request.POST['token']
        if booru_key == FULL_BOORU_KEY:
            request.session['booru_key'] = booru_key
            request.session['type'] = "FULL"
            request.session['key'] = True
            return HttpResponseRedirect('../booru')
        elif booru_key == "update":
            return HttpResponseRedirect('../update')            
        else:
            subooru = Subooru.objects.filter(key=booru_key).first()
            if subooru:
                request.session['booru_key'] = booru_key
                request.session['type'] = "SUB"
                return HttpResponseRedirect('../booru')
            else:
                return HttpResponseRedirect('/')

        
def booru(request):
    if request.session['key']: #Current session is approved
        if request.session['type'] == "SUB":
            booru_key = request.session['booru_key']
            subooru = Subooru.objects.get(key=booru_key)
            total_files = subooru.files.all().count()
        else:
            total_files = File.objects.count()      
        return render(request, 'booru/booru.html', {
            'total_posts': total_files, 
            #'all_tags': Tag.objects.all().order_by('count')
            })
    else:
        return HttpResponseRedirect("/") #not authorized, redired to login

#/thumbnail/<id>
def thumbnail(request, id):
    return HttpResponse(getThumbnail(request, id))

def image(request, id):
    return HttpResponse(getImage(request, id))

# /view/<id>
def view(request, id):
    raw_tags = request.GET['tags']
    tags = raw_tags.split(',')
    title = ""
        
    for i in range(0, len(tags)):
        tags[i] = "\"" + str.strip(tags[i]) + "\"" 
                       
    ids = getIdsFromHydrus(request, *tags)
    
    canCycle = False
    nextPost = -1
    previousPost = -1
    
    if len(ids) > 1:
        canCycle  = True 
        
    if canCycle:
        if int(id) == ids[-1]:
            nextPost = ids[0]
        else:
            nextPost = ids[ids.index(int(id)) + 1]
            
        if int(id) == ids[0]:
            previousPost = ids[-1]
        else:
            previousPost = ids[ids.index(int(id)) - 1]
    
    
    
    fileData = getMetaDataFromHydrusById(request, id)
    """ 
    This has a small issue of displaying siblings, which we can't look up. So if something is tagged "rating: mature" 
    then we get both "rating: mature" and "rating: explicit", but if "rating:mature" is the one that's replaced (by "explicit")
    then clicking the tag will cause an empty search. Need a way to get the master-tag or to do a "or" search of all siblings
    """
    if len(fileData['service_names_to_statuses_to_tags']) != 0:
        tags, title = cleanTags(*fileData['service_names_to_statuses_to_tags']['all known tags']['0'])
    else:
        tags, title = [],"Shepbooru"
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
        'raw_tags': raw_tags,
        'tags':tags,
        'urls': urls,
        'type': file_type,
        'mime': fileData['mime'],
        'height': height,
        'width': width,
        'title': title,
        'canCycle': canCycle,
        'nextPost': nextPost,
        'previousPost': previousPost
    })
    
# view/full/<id>
def fullImage(request, id):
    tags = request.GET['tags']
    fileData = getMetaDataFromHydrusById(request, id)
    file_type = getFileType(fileData['mime'])
    if len(fileData['service_names_to_statuses_to_tags']) != 0:
        title = cleanTags(*fileData['service_names_to_statuses_to_tags']['all known tags']['0'])[1]
    else:
        title = "Shepbooru"
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
        'title': title,
        'tags': tags
    })


def search(request):
    #Server will use hydrus comma-delimination instead of space like others. Makes it a bit easier I feel
    if request.session.has_key('key'): #Current session is approved

        raw_tags = request.GET.get('tags', '')
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
        
        file_hashes = getHashesFromHydrus(request, *tags)
        file_ids = getIdsFromHydrus(request, *tags)
        
        file_data = []
        canCycle = len(file_hashes) > 1
        # Figuring out what is okay and what is not
        if request.session['type'] == "SUB":
            allowed_hashes = []
            display_hashes = []
            display_ids = []
            sub = Subooru.objects.get(key=request.session['booru_key'])
            allowed_files_qs = sub.files.all()
            for file in allowed_files_qs:
                allowed_hashes.append(file.hash)
                
            for hash in allowed_hashes:
                if hash in file_hashes:
                    display_hashes.append(hash)
                    display_ids.append(file_ids[file_hashes.index(hash)])
        else:
           display_hashes = file_hashes
           display_ids = file_ids 
                
        for index, id in enumerate(display_ids[page_start:page_end]):  
            meta = getMetaDataFromHydrusById(request, id)
            
            if canCycle:
                if id == file_ids[-1]:
                    nextResult = file_ids[0]
                else:
                    nextResult = file_ids[index + 1]
                    
                if id == file_ids[0]:
                    previousResult = file_ids[-1]
                else:
                    previousResult = file_ids[index - 1]
                    
            file_data.append(
                {
                    'id': id,
                    'hash': display_hashes[index],
                    'isVideo': isAnimated(meta['mime']),
                    'hasAudio': meta['has_audio'],
                    'canCycle': canCycle,
                    'nextResult': nextResult,
                    'previousResult': previousResult                                        
                })


        #pagination        
        paginator = Paginator(display_ids, PAGE_SIZES)
        try:
            page_obj = paginator.page(page_num) #get the apporpriate page
        except PageNotAnInteger:
            page_obj = paginator.page(1)    #Return to page 1 if invalid page
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)  #return to last page if going too far
        
        return render(request, 'booru/results.html', {
            'data': file_data,
            'tag_string': cleaned_tags_string,
            'raw_tags': raw_tags,
            'page_obj': page_obj,
            'page' : 1,
            'title': title,
            'total' : len(display_hashes),
            'page_size': PAGE_SIZES,
            'canAddToSubooru': request.session['type'] != "SUB"
            # 'top_tags': getTagsOfIds(request, *file_ids),
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
        if not tag.startswith('\"'):
            tag_string += '\"' + tag + "\","
        else:
            tag_string += tag + ","
    tag_string = tag_string[:-1]
    tag_string = tag_string + ",\"system:archive\"]"
    url = urllib.parse.quote(tag_string)
    return url

#TODO: need to handle siblings. For example, "rating:e" returns nothing because it's got the sibling "rating:explicit"
def getIdsFromHydrus(request, *tags) -> list:
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + "/get_files/search_files?tags="
        url += tagsToHydrusString(*tags)
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        ids = res.json()['file_ids']
        
        #take the tags, and then do a search based on the tag

        return ids 
    
def getHashesFromHydrus(request, *tags) -> list:
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + "/get_files/search_files?tags="
        url += tagsToHydrusString(*tags)
        url += "&return_hashes=true"
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        ids = res.json()['hashes']
        
        #take the tags, and then do a search based on the tag

        return ids  

def getThumbnail(request, hydrus_id):
    url = getenv('HYDRUS_BASE') + "/get_files/thumbnail?file_id=" + str(hydrus_id)
    res = requests.get(url, headers={
        'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
        'User-Agent': "Pydrus-Client/1.0.0"
    })
    return res.content  

def getImage(request, hydrus_id):
    url = getenv('HYDRUS_BASE') + "/get_files/file?file_id=" + str(hydrus_id)
    res = requests.get(url, headers={
        'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
        'User-Agent': "Pydrus-Client/1.0.0"
    })
    return res.content  

def getThumbnailUrlFromId(request, id):
    if request.session['key']:
        """ This is absolutely influenced by hyshare """
        return (getenv('HYDRUS_BASE') + 'get_files/thumbnail?id=' + str(id) + '&Hydrus-Client-API-Access-Key=' + HYDRUS_AUTH_KEY)
    return ""

def getFileUrlFromId(request, id):
    if request.session['key']:
        """ This is absolutely influenced by hyshare """
        return (getenv('HYDRUS_BASE') + '/get_files/file?file_id=' + str(id) + '&Hydrus-Client-API-Access-Key=' + HYDRUS_AUTH_KEY)
    return ""

def getMetaDataFromHydrusById(request, id):
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + '/get_files/file_metadata?file_ids=[' + str(id) + ']'
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        data = res.json()['metadata'][0]
        return data
    
def getMetaDataFromHydrusByHash(request, hash):
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + '/get_files/file_metadata?hashes=%5b%22' + hash + '%22%5D'
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        data = res.json()['metadata'][0]
        return data
    
def getMetaOfIds(request, *ids):
    if request.session['key']:
        url = getenv('HYDRUS_BASE') + '/get_files/file_metadata?file_ids='
        tag_string = "["
        for tag in ids:
            tag_string += str(tag) + ","
        tag_string = tag_string[:-1]
        tag_string = tag_string + "]"
        url += urllib.parse.quote(tag_string)
        res = requests.get(url, headers={
            'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
            'User-Agent': "Pydrus-Client/1.0.0"
        })
        data = res.json()['metadata']
        return data
    
def cleanTags(*tags:str):
    """ Take a list of tags and remove certain ones that aren't important for the booru.
    Namely, removes meta:* , booru:*, filename:*, and source:* """
    
    """ Tags are tupled
        Tag[0] = the actual string of the tag
        Tag[1] = the type of tag, broken down as follows
            0 : standard
            1 : artist
            2 : series
            3 : rating
            4 : medium
            
    """
    cleanTags = []
    title = "Shepbooru"
    for tag in tags:
        tag = tag.replace('_',' ')

        if tag.startswith('title:'):
            title = tag[6:]
            continue
        
        if tag.startswith('creator:'):
            #in the event it's listed as a regular tag
            if (tag[8:], 0, tag[8:]) in cleanTags:
                cleanTags.remove( (tag[8:], 0, tag[8:]))
            cleanTags.append( (tag[8:], 1, tag[8:]) )
            continue
        
        if tag.startswith('character:'):
            #in the event it's listed as a regular tag
            if (tag[10:], 0, tag[10:]) in cleanTags:
                cleanTags.remove( (tag[10:], 0, tag[10:]))
            cleanTags.append( (tag[10:], 1, tag[10:]) )
            continue
        
        if tag.startswith('series:'):
            if (tag[7:], 0, tag[7:]) in cleanTags:
                cleanTags.remove( (tag[7:], 0, tag[7:]))
            cleanTags.append( (tag[7:], 2, tag))
            continue
            
        if tag.startswith('rating:'):
            if (tag[7:], 0, tag[7:]) in cleanTags:
                cleanTags.remove( (tag[7:], 0, tag[7:]))
            cleanTags.append( (tag[7:] , 3, tag))
            continue
        
        if tag.startswith('medium:'):
            if (tag[7:], 0, tag[7:]) in cleanTags:
                cleanTags.remove( (tag[7:], 0, tag[7:]))
            cleanTags.append( (tag[7:] , 4, tag))
            continue
        
        if not tag.startswith(('booru:', 'filename:', 'meta:', 'source:', 'pixiv work:', 'genre:')) and tag not in cleanTags:
            cleanTags.append( (tag, 0, tag) )
        
        #sort by type then name, grouping the specialty tags first.
        #since the tag type is an int, we can just negate it and put them at the top
        # subtract 1 because -0 is still 0, so it'd always be the top result
        cleanTags.sort(key=lambda tup: (-(tup[1] - 1), tup[0]))
        
    return cleanTags, title

        
def create_subooru(request):
    if request.method == 'POST':
        form = SubooruForm(request.POST)
        if form.is_valid():
            instance = form.save()
            value = instance.pk.hex
            return HttpResponse(f"Created a new subooru with the following hex.<br><b>{value}</b><br>Be sure to copy this key, it's how you open and edit the subooru you created")
    else:
        form = SubooruForm()
    return render(request, 'booru/create_subooru.html', {'form':form})

def add_to_booru(request):
    #Create a new Booru_File_Pair with the booru and file for values
    uid = request.POST.get("booru_uid")
    hashes = request.POST.getlist("hashes")
    existing_hashes = []
    sub = Subooru.objects.filter(key=uid).first()
             
    page = request.POST.get("page")
    if sub:
        for file in sub.files.all():
            existing_hashes.append(file.hash)
        for hash in hashes:
            if hash in existing_hashes:
                hashes.remove(hash)
        for hash in hashes:
            sub.files.add(File.objects.get(hash=hash))
        sub.save()
    return HttpResponseRedirect(page)

def add_all_to_subooru(request):
    buid = request.POST.get("booru")
    tags = request.POST.get("tags")
    page = request.POST.get("page")
    
    sub = Subooru.objects.filter(key=buid).first()
    if sub:    
        tags = tags.split(',')
        existing_hashes = []
        for file in sub.files.all():
            existing_hashes.append(file.hash) 
        hashes = getHashesFromHydrus(request, *tags)
        for hash in hashes:
            if hash in existing_hashes:
                hashes.remove(hash)
        
        files_to_add = File.objects.filter(hash__in=hashes)
        sub.files.add(*files_to_add)
        sub.save() 
    return HttpResponseRedirect(page)
    
    
    
def updateTables(request):
    if request.GET.get('delete', 'false' ) == 'true':
        File.objects.all().delete()
    
    #get tags
    # We're only going to worry about the actual files for now, tags MAY come later
    # url = getenv('HYDRUS_BASE') + "/add_tags/search_tags?search=*"
    # res = requests.get(url, headers={
    #     'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
    #     'User-Agent': "Pydrus-Client/1.0.0"
    # }) 
    # json_res = res.json()
    # for tag in json_res['tags']:
    #     tagEntry = Tag.objects.filter(name=tag['value']).first()
    #     if tagEntry == None:
    #         print(f"Adding tag {tag}\r", end='')
    #         TagModel = Tag(name=tag['value'], count=tag['count'])
    #         TagModel.save()
    #     else:
    #         if tagEntry.count != tag['count']:
    #             tagEntry.count = tag['count']
    #             tagEntry.save()
    #             print("Updated count of tag", tagEntry)
    #         else:
    #             print(f"Tag {tag} already in DB\t\t\t\t\r", end='')
        
    url = getenv('HYDRUS_BASE') + "/get_files/search_files?return_hashes=true"
    res = requests.get(url, headers={
        'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
        'User-Agent': "Pydrus-Client/1.0.0",
    }) 
    hash_json_res = res.json()
    url = getenv('HYDRUS_BASE') + "/get_files/search_files"
    res = requests.get(url, headers={
        'Hydrus-Client-API-Access-Key': HYDRUS_AUTH_KEY,
        'User-Agent': "Pydrus-Client/1.0.0",
    }) 
    id_json_res = res.json()
    json_res = zip(hash_json_res['hashes'], id_json_res['file_ids'])
    files = File.objects.values_list('hash', 'id')
    iter = 1
    total = len(id_json_res['file_ids'])
    for file_hash, file_id in json_res:
        print(f"Processing file {iter}  of  {total}\r", end="")
        if (file_hash, file_id) not in files:
            FileModel = File(hash=file_hash, id=file_id)
            FileModel.save()
        iter += 1
    
    return HttpResponseRedirect('/')
            
def getTagsOfIds(request, *ids):
    #poll hydrus for all these ids, then compile a list of all their tags
    tagDict = dict()
    for id in ids:
        fileData = getMetaDataFromHydrusById(request, id)
        if len(fileData['service_names_to_statuses_to_tags']) != 0:
            tags = fileData['service_names_to_statuses_to_tags']['all known tags']['0']
            tags = cleanTags(*tags)[0]
            for tag in tags:
                if tagDict.get(tag) != None:
                    val = tagDict.get(tag) + 1
                    tagDict[tag] = val
                else:
                    tagDict[tag] = 1
    
    return sorted(tagDict)[0:25]