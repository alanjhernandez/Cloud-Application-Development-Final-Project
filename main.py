from google.cloud import datastore
from google.auth.transport import requests
from flask import Flask, request, jsonify
import constants
from google.oauth2 import id_token
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
client = datastore.Client()

REDIRECT_URI = "https://project-hernalan.wl.r.appspot.com/profile"
CLIENT_SECRET = "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"
CLIENT_ID = "501517249915-pea5l61rltr4oq4tn8djijqpkunuppe4.apps.googleusercontent.com"
TOKEN_URI = "https://accounts.google.com/o/oauth2/token"
SCOPE = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'openid']
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
OAUTH = OAuth2Session(client_id = CLIENT_ID, redirect_uri = REDIRECT_URI, scope = SCOPE)

def checkJWT():
    jwt_token = request.headers.get('Authorization')
    if jwt_token:
        jwt_token = jwt_token.split(" ")[1]

        try:
            jwt_sub = id_token.verify_oauth2_token(jwt_token, requests.Request(), CLIENT_ID)[constants.sub]
        except:
            jwt_sub = "not valid"
            return jwt_sub
    else:
        jwt_sub = "not found"
        return jwt_sub
    return jwt_sub

@app.route('/')
def home():
    auth_url, state = OAUTH.authorization_url(AUTH_URI, access_type = "offline", prompt = "select_account")
    return '<h1>Welcome to the Final Project Home Page</h1>\n <p>Please click <a href=%s>here</a> to sign in to an account or create a new acocunt</p>' % auth_url

@app.route('/artists/<artist_id>', methods=["GET"])
def get_artist_id(artist_id):
    if request.method == "GET":
        jwt_sub = checkJWT()

        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if jwt_sub != artist_id:
            return(jsonify("you do not have access to this artist"), 404)
        
        if "application/json" in request.accept_mimetypes:
            query = client.query(kind = constants.artists)
            query.add_filter(constants.sub, "=", artist_id)
            artists = list(query.fetch())

            if len(artists) == 0:
                return(jsonify("artist does not exist"), 404)
            for e in artists:
                e[constants.id] = e.key.id
                e[constants.self] = request.url
            return(jsonify(artists), 200)
        else:
            result = (jsonify("requested MIME type is not supported"))
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = (jsonify("method not recognized"))
        result.status_code = 405
        result.mimetype = "application/json"
        return result

@app.route('/albums', methods =["GET", "POST"])
def get_post_albums():
    if request.method == "POST":
        jwt_sub = checkJWT()
        print(jwt_sub)
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            if "application/json" not in request.content_type:
                result = (jsonify("sent MIME type is not supported"))
                result.status_code = 406
                result.mimetype = "application/json"
                return result
            content = request.get_json()
            if len(content) != 6:
                return(jsonify("the album is missing some of the required attributes"), 400)
            create_album = datastore.entity.Entity(key=client.key("albums"))
            create_album.update({"title": content["title"], "genre": content["genre"], "release_date": content["release_date"], "label": content["label"], "owner": jwt_sub, "tracks": []})
            client.put(create_album)
            create_album.update({"id": create_album.id, "self": request.url + "/" + str(create_album.key.id)})
            if "application/json" in request.accept_mimetypes:
                result = jsonify(create_album)
                result.status_code = 201
                result.mimetype = "application/json"
            return result
        else:
            result =(jsonify("requested MIME type is not supported"))
            result.status_code =406
            result.mimetype = "application/json"
            return result
    elif request.method == "GET":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            query = client.query(kind = "albums")
            query.add_filter(constants.owner, "=", jwt_sub)
            q_limit = int(request.args.get("limit", "5"))
            q_offset = int(request.args.get("offset", "0"))
            l_iterator = query.fetch(limit = q_limit, offset = q_offset)
            pages = l_iterator.pages
            albums = list(next(pages))
            if l_iterator.next_page_token:
                next_offset = q_offset + q_limit
                next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            else:
                next_url = None
            for e in albums:
                e[constants.id] = e.key.id
                e[constants.self] = request.url_root + "albums/" + str(e[constants.id])
            albums_list = {"albums": albums}
            if next_url:
                albums_list["next"] = next_url

            albums_list["collection"] = len(list(query.fetch()))
            result = (jsonify(albums_list))
            result.status_code = 200
            result.mimetype = "application/json"
            return result
        else:
            result = (jsonify("requested MIME type is not supported"))
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = (jsonify("this method is not recognized"))
        result.mimetype = "application/json"
        result.status_code = 405
        return result

@app.route('/artists', methods=["GET"])
def get_artists():
    if request.method == "GET":
        if "application/json" in request.accept_mimetypes:
            query = client.query(kind = constants.artists)
            artists = list(query.fetch())

            for e in artists:
                e[constants.id] = e.key.id
                e[constants.self] = request.url + "/" + str(e[constants.id])
            return(jsonify(artists), 200)
        else:
            result = (jsonify("requested MIME type is not supported"))    
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = (jsonify("method not recognized"))
        result.status_code = 405
        result.mimetype = "application/json"
        return result

@app.route('/profile')
def profile_route():
    token = OAUTH.fetch_token(TOKEN_URI, authorization_response = request.url, client_secret = CLIENT_SECRET)
    profile_info = id_token.verify_oauth2_token(token[constants.token], requests.Request(), CLIENT_ID)
    query = client.query(kind = constants.artists)
    query.add_filter(constants.sub, "=", profile_info[constants.sub])
    result = list(query.fetch())
    if len(result) == 1:
        return(("<h1>Hello again</h1>\n <p>Your JWT is: %s</p>\n <p>Your unique sub id is: %s</p>\n" % (token[constants.token], profile_info[constants.sub])), 200)
    if len(result) == 0:
        create_profile = datastore.entity.Entity(key = client.key(constants.artists))
        create_profile.update({"email": profile_info[constants.email], "sub": profile_info[constants.sub]})
        client.put(create_profile)
        return(("<h1>A new account has been created</h1>\n <p>Your generated JWT is: %s</p>\n <p>Your generated unique sub id is: %s</p>\n" % (token[constants.token], profile_info[constants.sub])), 201)



@app.route('/albums/<album_id>', methods =["GET", "DELETE", "PUT", "PATCH"])
def delete_put_albums(album_id):
    if request.method == "PUT":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            if "application/json" not in request.content_type:
                result = (jsonify("sent MIME type is not supported"))
                result.status_code = 406
                result.mimetype = "application/json"
                return result
            album_key = client.key("albums", int(album_id))
            album = client.get(key=album_key)
            if album == None:
                return(jsonify("this album cannot be found"), 401)
            if album[constants.owner] != jwt_sub:
                return(jsonify("cannot change this album"),401)
            content = request.get_json()
            if len(content) == 0:
                return(jsonify("invalid info"), 400)
            client.put(album)
            album[constants.id] = album.key.id
            album[constants.self] = request.url
            result = (jsonify(album))
            result.mimetype = "application/json"
            result. status_code = 303
            result.headers.set('Location', request.base_url)
            return result
        else:
            result =  (jsonify("requested MIME type is not supported"))
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    elif request.method == "PATCH":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            if "application/json" not in request.content_type:
                result = (jsonify("sent MIME type is not supported"))
                result.status_code = 406
                result.mimetype = "application/json"
                return result
            album_key = client.key("albums", int(album_id))
            album = client.get(key = album_key)
            if album == None:
                return(jsonify("this album could not be found"),401)
            if album[constants.owner] != jwt_sub:
                return(jsonify("cannot access this album"), 401)
            content = request.get_json()
            if len(content) == 0:
                return(jsonify("invalid content"), 400)
            client.put(album)
            album[constants.id] = album.key.id
            album[constants.self] = request.url

            result = (jsonify(album))
            result.status_code = 201
            result.mimetype = "application/json"
            return result
        else:
            result = (jsonify("request MIME type is not supported"))
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    elif request.method == "GET":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            album_key = client.key("albums", int(album_id))
            album = client.get(key = album_key)
            if album == None:
                return(jsonify("this album cannot be found"), 404)
            if album[constants.owner] != jwt_sub:
                return(jsonify("cannot access this album"), 401)
            album[constants.id] = album.key.id
            album[constants.self] = request.url

            if album[constants.tracks]:
                for track in album[constants.tracks]:
                    track_key = client.key("tracks", track[constants.id])
                    self_track = client.get(key=track_key)
                    track["title"] = self_track["title"]
                    track["release_date"] = self_track["release_date"]
                    track["track_number"] = self_track["track_number"]
                    track["b_side"] = self_track["b_side"]
                    track["self"] = request.url_root + "albums/" + str(track[constants.id])
            result = (jsonify(album))
            result.status_code = 200
            result.mimetype = "application/json"
            return result
        else:
            result = (jsonify("requested MIME type is not supported"))
            result.mimetype = "application/json"
            result.status_code = 406
            return result
    elif request.method == "DELETE":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            album_key = client.key("albums", int(album_id))
            album = client.get(key = album_key)
            if album == None:
                return(jsonify("album not found"), 401)
            if album[constants.owner] != jwt_sub:
                return (jsonify("you are not part of this album"), 401)
            if album[constants.tracks]:
                for track in album[constants.tracks]:
                    track_key = client.key("tracks", track[constants.id])
                    self_track = client.get(key = track_key)
                    self_track["album_id"] = None
                    client.put(self_track)
            client.delete(album)
            result = (jsonify(""))
            result.status_code = 204
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = jsonify("method is not recognized")
        result.status_code = 405
        result.mimetype = "application/json"
        return result
    
@app.route('/tracks', methods=["GET", "POST"])
def get_post_tracks():
    if request.method == "POST":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            if "application/json" not in request.content_type:
                result = jsonify("sent MIME type is not supported")
                result.status_code = 406
                result.mimetype = "application/json"
                return result
            content = request.get_json()

            if len(content) != 4:
                return (jsonify("The track is missing at least one required attribute"), 400)
            new_track = datastore.entity.Entity(key=client.key("tracks"))
            new_track.update({"title": content["title"], "album_id": None, "b_side": False, "release_date": content["release_date"], "track_number": content["track_number"], "owner": jwt_sub})
            client.put(new_track)
            new_track.update({"id": new_track.key.id, "self": request.url + "/" + str(new_track.key.id)})

            if "application/json" in request.accept_mimetypes:
                result = jsonify(new_track)
                result.status_code = 201
                result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    elif request.method == "GET":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            query = client.query(kind = "tracks")
            query.add_filter(constants.owner, "=", jwt_sub)
            q_limit = int(request.args.get("limit", "5"))
            q_offset = int(request.args.get("offset", "0"))
            l_iterator = query.fetch(limit= q_limit, offset= q_offset)
            pages = l_iterator.pages
            track_list = list(next(pages))
            if l_iterator.next_page_token:
                next_offset = q_offset + q_limit
                next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            else:
                next_url = None
            for e in track_list:
                e[constants.id] = e.key.id
                e[constants.self] = request.url_root + "tracks/" + str(e.key.id)
            tracks = {"tracks": track_list}
            if next_url:
                tracks["next"] = next_url
            tracks["collection"] = len(list(query.fetch()))
            result = jsonify(tracks)
            result.status_code = 200
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = jsonify("this method is not recognized")
        result.status_code = 405
        result.mimetype = "application/json"
        return result

@app.route('/tracks/<track_id>', methods = ["GET", "PATCH", "DELETE", "PUT"])
def tracks_put_etc(track_id):
    if request.method == "PUT":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            if "application/json" not in request.content_type:
                result = jsonify("sent MIME type is not supported")
                result.status_code = 406
                result.mimetype = "application/json"
                return result
            track_key = client.key("tracks", int(track_id))
            track = client.get(key = track_key)
            if track == None:
                return (jsonify("this track nannot be found"), 404)
            if track[constants.owner] != jwt_sub:
                return (jsonify("you do not have this track"), 401)
            content = request.get_json()
            if len(content) != 4:
                return(jsonify("invalid content"), 400)
            
            for i in content:
                if i == "b_side" and type(content.get(i)) == bool:
                    if track["album_id"]:
                        album_key = client.key("albums", int(track["album_id"]))
                        album = client.get(key=album_key)
                        if track["b_side"] ==False and content.get(i) == True:
                            album["tracks"].remove({"id": track.key.id, "owner": jwt_sub, "album_id": str(album.key.id)})
                        elif track["b_side"] ==True and content.get(i) == False:
                            album["tracks"].append({"id": track.key.id, "owner": jwt_sub, "album_id": str(album.key.id)})
                        client.put(album)
                    album["b_side"] = content.get(i)
                elif type(content.get(i)) == str and i == "title":
                    track["title"] = content.get(i)
                elif type(content.get(i)) == str and i == "release_date":
                    track["release_date"] = content.get(i)
                elif type(content.get(i)) == int and i == "track_number":
                    track["track_number"] = content.get(i)
                else:
                    return (jsonify("invalid content"), 400)
            client.put(track)
            track[constants.id] = track.key.id
            track[constants.self] = request.url

            result = jsonify(track)
            result.status_code = 201
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    elif request.method == "GET":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            track_key = client.key("tracks", int(track_id))
            track = client.get(key = track_key)
            if track == None:
                return (jsonify("this track cannot be found"), 404)
            if track[constants.owner] != jwt_sub:
                return (jsonify("you do not have this track"), 401)
            track[constants.id] = track.key.id
            track[constants.self] = request.url

            result = jsonify(track)
            result.status_code = 200
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    elif request.method == "PATCH":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            if "application/json" not in request.content_type:
                result = jsonify("sent MIME type is not supported")
                result.status_code = 406
                result.mimetype = "application/json"
                return result
            track_key = client.key("tracks", int(track_id))
            track = client.get(key = track_key)
            if track == None:
                return (jsonify("this track cannot be found"), 404)
            if track[constants.owner] != jwt_sub:
                return (jsonify("you do not have this track"), 401)
            content = request.get_json()
            if len(content) == 0:
                return (jsonify("invalid content"), 400)
            for i in content:
                if i == "b_side" and type(content.get(i)) == bool:
                    if track["album_id"]:
                        album_key = client.key("albums", int(track["album_id"]))
                        album = client.get(key=album_key)
                        if track["b_side"] ==False and content.get(i) == True:
                            album["tracks"].remove({"id": track.key.id, "owner": jwt_sub, "album_id": str(track.key.id)})
                        elif track["b_side"] ==True and content.get(i) == False:
                            album["tracks"].append({"id": track.key.id, "owner": jwt_sub, "album_id": str(track.key.id)})
                        client.put(album)
                    album["b_side"] = content.get(i)                        
                elif type(content.get(i)) == str and i == "title":
                    track["title"] = content.get(i)
                elif type(content.get(i)) == str and i == "release_date":
                    track["release_date"] = content.get(i)
                elif type(content.get(i)) == int and i == "track_number":
                    track["track_number"] = content.get(i)
                else:
                    return (jsonify("invalid content"), 400)
            client.put(track)
            track[constants.id] = track.key.id
            track[constants.self] = request.url

            result = jsonify(track)
            result.status_code = 201
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    elif request.method == "DELETE":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            track_key = client.key("tracks", int(track_id))
            track = client.get(key = track_key)
            if track == None:
                return (jsonify("this track cannot be found"), 404)
            if track[constants.owner] != jwt_sub:
                return (jsonify("you do not have this track"), 401)
            if track["album_id"]:
                album_key = client.key("albums", int(track["album_id"]))
                album = client.get(key = album_key)
                client.put(album)
            client.delete(track)
            result = jsonify("")
            result.status_code = 204
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = jsonify("this method is not recognized")
        result.status_code = 405
        result.mimetype = "application/json"
        return result

@app.route('/albums/<album_id>/tracks', methods=["GET", "POST"])
def get_post_tracks_albums(album_id):
    if request.method == "GET":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            album_key = client.key("albums", int(album_id))
            album_choice = client.get(key = album_key)
            if album_choice == None:
                return(jsonify("this album cannot be found"), 401)
            if album_choice[constants.owner] != jwt_sub:
                return (jsonify("you are not in this album"), 401)
            query = client.query(kind = constants.tracks)
            query.add_filter("album_id", "=", album_id)
            query.add_filter("b_side", "=", False)
            tracks = list(query.fetch())
            for e in tracks:
                e[constants.id] = e.key.id
                e[constants.self] = request.url_root + "tracks/" + str(e[constants.id])
            total_albums = {"tracks": tracks}
            result = jsonify(total_albums)
            result.status_code = 200
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    elif request.method == "POST":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            if "application/json" not in request.content_type:
                result = jsonify("sent MIME type is not supported")
                result.status_code = 406
                result.mimetype = "application/json"
                return result
            album_key = client.key("albums", int(album_id))
            album = client.get(key = album_key)

            if album == None:
                return (jsonify("this album cannot be found"), 401)
            if album[constants.owner] != jwt_sub:
                return(jsonify("you are not part of this album"),401)
            content = request.get_json()
            if len(content) != 5:
                return (jsonify("at least one required attribute is missing"), 400)
            new_track = datastore.entity.Entity(key = client.key(constants.tracks))
            new_track.update({"title": content["title"], "album_id": album_id, "b_side": False, "release_date": content["release_date"], "track_number": content["track_number"], "owner": jwt_sub})
            client.put(new_track)
            album[constants.tracks].append({"id": new_track.key.id, "owner": jwt_sub, "album_id": album_id})
            client.put(album)
            album.update({"id": album.key.id, "self": request.url_root + "albums/" + str(album.key.id)})
            for track in album[constants.tracks]:
                track[constants.self] = request.url_root + "tracks/" + str(track[constants.id])
            if "application/json" in request.accept_mimetypes:
                result = jsonify(album)
                result.status_code = 201
                result.mimetype = "application/json"
            return result 
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = jsonify("this method is not recognized")
        result.status_code = 405
        result.mimetype = "application/json"
        return result

@app.route('/albums/<album_id>/tracks/<track_id>', methods = ["PUT", "DELETE"])
def delete_put_tracks_albums(album_id, track_id):
    if request.method == "PUT":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)       
                     
        album_key = client.key("albums",int(album_id))
        album = client.get(key = album_key)

        track_key = client.key("tracks", int(track_id))
        track = client.get(key = track_key)

        if track == None and album == None:
            return (jsonify("cannot find both track nor album"), 404)
        
        if album == None:
            return (jsonify("this album could not be found"), 404)
        if track == None:
            return (jsonify("this track could not be found"), 404)
        if album[constants.owner] != jwt_sub:
            return (jsonify("you are not part of this album"), 401)
        if track[constants.owner] != jwt_sub:
            return (jsonify("you do not have this track"), 401)

        for self_track in album[constants.tracks]:
            if self_track[constants.id] == int(track_id):
                return(jsonify("this track is already part of the album"), 403)
        album["tracks"].append({"id": track.key.id, "owner": track["owner"], "album_id": album_id})
        client.put(album)

        track["album_id"] = album_id
        client.put(track)
        result = jsonify("")
        result.status_code = 204
        result.mimetype="application/json"
        return result
    elif request.method == "DELETE":
        jwt_sub = checkJWT()
        if jwt_sub == "not valid":
            return(jsonify("wrong jwt"), 401)
        if jwt_sub == "not found":
            return(jsonify("no jwt found"), 401)
        if "application/json" in request.accept_mimetypes:
            album_key = client.key("albums", int(album_id))
            album = client.get(key=album_key)
            track_key = client.key("tracks", int(track_id))
            track = client.get(key = track_key)

            if track == None and album == None:
                return (jsonify("cannot find both track nor album"), 404)
            
            if album == None:
                return (jsonify("this album cannot be found"), 404)
            if track == None:
                return (jsonify("this track cannot be found"), 404)
            if album[constants.owner] != jwt_sub:
                return (jsonify("you are not part of this album"), 401)
            elif track[constants.owner] != jwt_sub:
                return (jsonify("you do not have this track"), 401)
            if track["album_id"]:
                album_key = client.key("albums", int(track["album_id"]))
                album = client.get(key = album_key)
                if track["b_side"] == False:
                    album["tracks"].remove({"id": track.key.id, "owner": jwt_sub, "album_id": str(album.key.id)})
                client.put(album)
            client.delete(track)
            result = jsonify("")
            result.status_code = 204
            result.mimetype = "application/json"
            return result
        else:
            result = jsonify("requested MIME type is not supported")
            result.status_code = 406
            result.mimetype = "application/json"
            return result
    else:
        result = jsonify("this method is not recognized")
        result.status_code = 405
        result.mimetype = "application/json"
        return result

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)