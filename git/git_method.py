#encoding:utf-8
# -*- coding: utf-8 -*-
#!/usr/bin/env python2.7
import re
import requests,sys,json,logging,time,datetime,os
import gitdiff_util as util
from threading import Timer
# import for_linux_config as ProConfig
ConfigUrl="./config.ini"
# reload(sys)
sys.setdefaultencoding('utf-8')
HistoryTimeStamp=1511870939000
HistoryId="c8799ca4d44ad4f1ab5cb0243f3a2b81ced59063"
newTimeStamp=0
newId=""
oldId=""

#此处循环其实时间倒序查询
def CycleGetFirstVersion(hjson,svnurl,user,pwd):
    global oldId
    # if (hjson['nextPageStart'] is not None) and hjson['isLastPage'] is False:
    if hjson['isLastPage'] is False:
        # print "islastpage"+ str(hjson['isLastPage'])
        url=("%s&start=%s" %(svnurl,str(hjson['nextPageStart'])))
        print "url is .........:"+url
        r = requests.get(url,auth=('%s' %user,'%s' %pwd))#('BL02957', 'zzy880728()'))
        r.headers['Content-Type'] = 'application/json'
        hjson1=json.loads(r.content)
        # tmpid=hjson1['values'][-1]['id']
        # print "first tmpid is"+tmpid
        # print "start:"+str(hjson1['nextPageStart'])
        CycleGetFirstVersion(hjson1,svnurl,user,pwd)
    else:
        oldId=hjson['values'][-1]['id']

def GetNewVersionInfo():
    global newId
    global newTimeStamp
    global oldId
    #文件里保存了历史已经对比的版本（时间戳+版本号）。从对应服务的commits页面读取当前变更的commits json，用时间戳做对比，拿到当前第一个跟历史版本
    #时间戳比较，如果大就读取变更文件。
    # github_url="http://bitbucket.rd.800best.com/projects/EXPRESS/repos/q9taobao/commits?decorator=none"
    github_url=util.getconfigbyCode('svnurl')
    if('?' in github_url):
    #修改地址，如果地址包好?那么增加条件需要加？
        #修改地址，如果地址包好?那么增加条件需要加？
        github_url="%s&limit=200" %github_url
        print "branch url is:" +github_url
    else:
        #修改地址，如果地址包好?那么增加条件需要加？
        github_url="%s?limit=200" %github_url
        print "branch url is:" +github_url

    #"http://bitbucket.rd.800best.com/rest/api/1.0/projects/EXPRESS/repos/q9taobao/commits?decorator=none"
    # data=json.dumps()
    print github_url
    user=util.getconfigbyCode('gituser')
    pwd=util.getconfigbyCode('gitpwd')
    r = requests.get(github_url,auth=('%s' %user,'%s' %pwd))#('BL02957', 'zzy880728()'))

    r.headers['Content-Type'] = 'application/json'
    print "hisStamp:"+util.getconfigbyCode('HisTimeStamp')

    hjson=json.loads(r.content)
    # print type(hjson) #返回的json组织成dict 可以拿到本次返回values,分页数：size,islastpage,start,limit,nextPage
    # print type(hjson['values'])
    #返回的values是一个列表，
    #里面包含了dict：id,displayid,author(name,emailAddress),authorTimestamp,committeer(name,emailAddress),committerTimestamp,messaget,parents
    if(util.getconfigbyCode('HisTimeStamp')=="0"):#如果配置里没有填写时间戳。
        newTimeStamp=hjson['values'][0]['committerTimestamp']
        newId=hjson['values'][0]['id']
        if hjson['isLastPage'] is False: #如果有分页数据那么需要读取当前分支地址的开始变更提交版本。那么就取当前版本提交库里的第一个起始做开始吧。
            print "start get id"
            CycleGetFirstVersion(hjson,github_url,user,pwd)
            print "end get id"
            print "cycle oldId is : "+oldId
            print "end get id111"
        else:
            oldId=hjson['values'][-1]['id']
        return newId

    if('?' in github_url):
        i=0
        newTimeStamp=HistoryTimeStamp
        newId=HistoryId
        for item in hjson['values']: #list类型
            # print "circle----"+str(item['committerTimestamp'])
            if(item['committerTimestamp']-long(util.getconfigbyCode('HisTimeStamp'))>0):
                i+=1
                newTimeStamp=hjson['values'][0]['committerTimestamp']
                newId=hjson['values'][0]['id']
                #如果是分支地址，包含？的地址，那么还需要拿到当前时间大于历史时间的最小值。
                #需要一直循环下去
                oldId=item['id']
            else:
                if(i>0):
                    return newId
                else:
                    return util.getconfigbyCode('HisId')
    else:
        for item in hjson['values']: #list类型
            # print item
            # print type(item) #dict类型
            # #按时间戳做排序 committerTimestamp 默认已经排序的
            # sorted(d.items(),lambda x,y:cmp(x[1],y[1],reverse=True))
            # print item['id']
            if(item['committerTimestamp']-long(util.getconfigbyCode('HisTimeStamp'))>0): #跟历史版本比，如果大于历史版本，那么就直接跟当前版本对比。
                    newTimeStamp=item['committerTimestamp']
                    newId=item['id']
                    print "has big"
                    return newId
            else:
                return util.getconfigbyCode('HisId')

def GetDiff():
    currentVersion=GetNewVersionInfo()
    print "currentVersion----"+currentVersion
    print newTimeStamp
    # diffUrl=github_url="http://bitbucket.rd.800best.com/rest/api/1.0/projects/EXPRESS/repos/q9taobao/diff"
    # r = requests.get(github_url,auth=('BL02957', 'zzy880728()'),params={'since':'c8799ca4d44ad4f1ab5cb0243f3a2b81ced59063','until':'65bb398fb062f14a414fb12f94c54f066ac69d5b'})
    diffUrl="%s/%s/diff" %(util.getconfigbyCode('svnurl').split('?')[0],currentVersion)#http://bitbucket.rd.800best.com/rest/api/1.0/projects/EXPRESS/repos/q9taobao/commits/c8799ca4d44ad4f1ab5cb0243f3a2b81ced59063/diff"
    print diffUrl
    hidId=""
    if(oldId.strip()):
        hidId=oldId
        print "current oldId is" +oldId
    else:
        hidId=util.getconfigbyCode('HisId')
    # oldId if not oldId.strip() else util.getconfigbyCode('HisId')
    print "hidId is"+hidId
    print "oldid----------"+hidId +"----"+currentVersion
    r = requests.get(diffUrl,auth=('BL02957', 'zzy880728()'),params={'since':hidId,'contextLines':1500}) #可以从版本号到当前地址的版本号params={'contextLines':1500})#
    r.headers['Content-Type'] = 'application/json'

    # t=json.dumps(r.content,indent=2)
    # print r.content
    # return r.content
    hjson=json.loads(r.content) #TODO:解析

    # print type(hjson)
    diffDic= hjson['diffs']
    addChangeData=[]
    # print type(diffDic) #list
    for data in diffDic: #data is dict,data's source destination is dict.
        #TODO:分两种情况：destination不存在的,那么就是删除数据。2.source不存在那么就是新增的数据。

        if data['destination'] and data['destination']['extension']=="java": #这些是变更的java文件，需要组装好对应的变更代码，再解析拿到变更方法。
            # print data['source']['name']
            className=data['destination']['name']
            packname=data['destination']['parent'].replace('/','.').split('.java.')[1]  #java有规律的命名和建立文件，一般是java文件放在java文件夹里，然后包名是com.best开始的。
            # print className
            # print packname
            # get diff text. data['hunks'] is list.
            changedTexts=[]
            for changedTxt in data['hunks']:#changedTxt is dict.
                if changedTxt['segments']: #changedTxt['segments'] is list.
                    for seg in changedTxt['segments']: #seg is dict.
                        if(seg['type']=="ADDED"):
                            for line in seg['lines']:#lines is list,line is dict
                                changedTexts.append("+L%s %s" %(line['destination'],line['line']))
                        elif(seg['type']=="REMOVED"):
                            for line in seg['lines']:#lines is list,line is dict
                                changedTexts.append("-L%s %s" %(line['destination'],line['line']))
                        else:
                            for line in seg['lines']:#lines is list,line is dict
                                changedTexts.append("L%s %s" %(line['destination'],line['line']))
            # print changedTexts
            # util.SaveChangeToTxt(className,changedTexts)
            changeMethodRealtions=util.getChangedMethodRelationInfo(changedTexts,packname,className) #获取到字典，key变更方法名的行,value:变更操作
            changeData=util.getQasParmsObjects(changeMethodRealtions)
            if len(changeData) > 0:
                for d in changeData:
                    addChangeData.append(d)
        elif data['source'] and data['source']['extension']=="java": #这些是变更的java文件，需要组装好对应的变更代码，再解析拿到变更方法。
            # print data['source']['name']
            className=data['source']['name']
            packname=data['source']['parent'].replace('/','.').split('.java.')[1]  #java有规律的命名和建立文件，一般是java文件放在java文件夹里，然后包名是com.best开始的。
            # print className
            # print packname
            # get diff text. data['hunks'] is list.
            changedTexts=[]
            for changedTxt in data['hunks']:#changedTxt is dict.
                if changedTxt['segments']: #changedTxt['segments'] is list.
                    for seg in changedTxt['segments']: #seg is dict.
                        if(seg['type']=="ADDED"):
                            for line in seg['lines']:#lines is list,line is dict
                                changedTexts.append("+L%s %s" %(line['source'],line['line']))
                        elif(seg['type']=="REMOVED"):
                            for line in seg['lines']:#lines is list,line is dict
                                changedTexts.append("-L%s %s" %(line['source'],line['line']))
                        else:
                            for line in seg['lines']:#lines is list,line is dict
                                changedTexts.append("L%s %s" %(line['source'],line['line']))

            util.SaveChangeToTxt(className,changedTexts)
            changeMethodRealtions=util.getChangedMethodRelationInfo(changedTexts,packname,className) #获取到字典，key变更方法名的行,value:变更操作
            changeData=util.getQasParmsObjects(changeMethodRealtions)
            if len(changeData) > 0:
                for d in changeData:
                    addChangeData.append(d)

        # print changedTexts
    return addChangeData

# GetDiff()
    # print json.dumps(hjson)
    # print hjson

def SendChange():
    projectName=util.getconfigbyCode('projectAlias')
    print ("projectName....%s" %projectName)
    changeDatas=GetDiff()
    changeCount=util.dealWithAllChangeMethodsForGit(changeDatas,projectName,newId,newTimeStamp)
    print changeCount
    msg=""
    if changeCount > 0:
        print "Have changes:"+str(changeCount)
        msg="%s from version:%s to %s have TotalChangeMethods:%s" %(projectName,str(oldId),str(newId),str(changeCount))
        util.ResetConfigValue('HisTimeStamp',newTimeStamp)
        util.ResetConfigValue('HisId',newId)
        # shutil.rmtree(tmpfold)
    elif newTimeStamp==0:
        msg="%s from version:%s to %s have no methods changed."  %(projectName,oldId,newId)
    else:
        msg="%s from version:%s to %s have no methods changed."  %(projectName,oldId,newId)
    print msg
    logging.info("svnSourceBusinessDeal result:%s" %msg)

def setLoggingInfo():
    # logging.basicConfig(filename='logger.log', level=logging.INFO)
    logging.basicConfig(filename=('logger_%s.log' %datetime.date.today()),format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)
    fmt = "%(asctime)-15s %(levelname)s %(filename)s %(lineno)d %(process)d %(message)s"
    datefmt = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)


#----------------------------------
# DealSvnSourceJob: 定时器，每隔多少时间执行一次任务
#----------------------------------
def dealGitSourceJob():#dealSvnSourceJob
    """
    Args:
        intervalTime:间隔时间，单位是秒。
    """
    try:
        time_stamp=datetime.datetime.now()
        print time_stamp.strftime('%Y.%m.%d-%H:%M:%S')
        SendChange()
        # t=Timer(intervalTime_sec,dealSvnSourceJob(intervalTime_sec))
        t=Timer(200, SendChange)
        t.start()
    except Exception as err:
        print "dealGitSourceJob Exception:%s" %str(err)
        logging.error("dealGitSourceJob Exception:%s" %str(err))
        print err


if __name__ == "__main__":
    if len(sys.argv)>1:
        ConfigUrl=sys.argv[1]
    if(os.path.isfile(ConfigUrl)):
        setLoggingInfo()
        util.setLoggingInfo()
        dealGitSourceJob()
    else:
        print u"配置文件路径：%s, 不存在" %str(ConfigUrl)
        logging.error(u"配置文件路径：%s, 不存在" %str(ConfigUrl))

