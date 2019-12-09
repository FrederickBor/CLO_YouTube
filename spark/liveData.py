from YoutubeDataAPI import YoutubeDataAPI
from datetime import datetime
import socket
import sys
import requests
import json
import os
import csv

def processVideos(apikey,regionCode):
    '''
    This class will be procesing all the information obtained by the YouTube Data API
    and process it to send it to spark.

    The given format will be a list of lists with the following format.

    videoID\tPublished At\tVideo Title\tDescription\tChannel Title\tChannel Subscribers\tTags\tView Count\tLike Count\tDislike Count\tFavorite Count\tComment Count
    '''
    yt = YoutubeDataAPI(apikey)
    part = "id,statistics,snippet"
    chart = "mostPopular"
    maxResults = "50"
    youtubeData = yt.getVideos(part=part,chart=chart,regionCode=regionCode,maxResults=maxResults)
    allVideos = list()
    end = False
    while (not end):
        if youtubeData != None:
            videos = youtubeData['items']

            for video in videos:
                # Obtain the channel information to have the number of subscribers.
                channelID = convertFormat(video['snippet']['channelId'])
                channelInformation = yt.getChannels('statistics',_id=channelID)

                try:
                    subscribers = int(channelInformation['statistics']['subscriberCount'])
                except:
                    subscribers = -1

                try:
                    tags = convertFormat(getDataInLine(video['snippet']['tags'],","))
                except:
                    tags = ""
                
                try:
                    commentCount = convertFormat(video['statistics']['commentCount'])
                except:
                    commentCount = 0
                
                # This dict was created to have a readable code.
                infoDict = {
                    "videoID" : convertFormat(video['id']),
                    "publishedAt" : convertFormat(video['snippet']['publishedAt']),
                    "videoTitle" : convertFormat(video['snippet']['title']),
                    "description" : convertFormat(video['snippet']['description']),
                    "channelTitle" : convertFormat(video['snippet']['channelTitle']),
                    "channelSubscribers" : subscribers,
                    "tags" : tags,
                    "viewCount" : convertFormat(video['statistics']['viewCount']),
                    "likeCount" : convertFormat(video['statistics']['likeCount']),
                    "dislikeCount" : convertFormat(video['statistics']['dislikeCount']),
                    "favoriteCount" : convertFormat(video['statistics']['favoriteCount']),
                    "commentCount" : commentCount
                }

                # Converts the previous dict to a list.
                valuesList = [ value for value in infoDict.values() ]
                allVideos.append(valuesList)
        try:
            nextPageToken = youtubeData["nextPageToken"]
            youtubeData = yt.getVideos(part=part,chart=chart,regionCode=regionCode,maxResults=maxResults,pageToken=nextPageToken)
        except:
            end = True
    return allVideos

def convertFormat(description):
    return description.replace("\r"," ") .replace("\n"," ").replace("\t"," ").replace('"'," ")

def getDataInLine(data,separator):
    '''
    Converts a list in a string.
    '''
    text = ""
    for value in data:
        text += str(value)
        if value != data[-1]:
            text += separator
    return text

def sentVideosToSpark(videos, tcp_connection):
    '''
    This function sends all the information given in videos to the spark app.
    '''
    for data in videos:
        try:
            strData = getDataInLine(data,"\t")
            print("Data Text: " + strData)
            print ("------------------------------------------")
            tcp_connection.send(strData + '\n')
        except:
            e = sys.exc_info()[0]
            print("Error: %s" % e)
    pass

def generateCSV(videos,regionCode):
    """
    This function creates a new csv file with all the information of the videos.
    """ 
    dt_string = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    file_name = regionCode + "_" + dt_string + ".csv"
    path = os.path.join(os.getcwd(),file_name)

    with open(path, 'w',newline='') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(["videoID","Published_at","Video_title","Description","Channel_title","Channel_subscribers","Tags","View_count","Like_count","Dislike_count","Favorite_count","Comment_count"])
        writer.writerows(videos)

    print("CSV file {} generated successfully.".format(file_name))
    pass


if __name__ == "__main__":
    apikey = "AIzaSyDbJzfwtRtzYEn_CC9eNoxFn5JjF7qRx_U"

    ## ARGUMENT PARSER
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("regionCode", help="Region code for the youtube videos")
    parser.add_argument("-m","--mode", help='live or csv, by default is csv')
    args = parser.parse_args()
    ## END OF ARGUMENT PARSER

    if (args.mode):
        if (args.mode == "live"):
            TCP_IP = "localhost"
            TCP_PORT = 9009
            conn = None
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((TCP_IP, TCP_PORT))
            s.listen(1)
            print("Waiting for TCP connection...")
            conn, addr = s.accept()
            print("Connected... Starting getting tweets.")
            resp = processVideos(apikey,args.regionCode)
            sentVideosToSpark(resp,conn)
        elif (args.mode == "csv"):
            resp = processVideos(apikey,args.regionCode)
            generateCSV(resp,args.regionCode)
        else:
            sys.exit(1)
    else:
        resp = processVideos(apikey,args.regionCode)
        generateCSV(resp,args.regionCode)

    
    pass