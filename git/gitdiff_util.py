#encoding:utf-8
# -*- coding: utf-8 -*-
#!/usr/bin/env python2.7
import os,sys,re,shutil,logging,time,datetime,ConfigParser,json,requests
from  configobj import ConfigObj
import sys
ConfigUrl="./config.ini"
reload(sys)
sys.setdefaultencoding('utf8')

def getChangedMethodRelationInfo(changedTexts,packname,className):
    """
    get changed method relation info:methodname,packagename,classname,parames,remark.
    Args:
        fileUrl:this file is the added +- tag source file text.是增加了+-标记的源码文件。
    Returns:
        Dictionary:packagename,classname,changed method list.
    """
    try:
        # print u"本地地址:%s" %fileurl
        change={} #其实还需要返回类信息
        result=[]
        i=0
        for line in changedTexts:
            line=line.strip()
            i+=1
            if not len(line) or line.startswith("//")or line.startswith("/*"):
                continue
            mayPackage=packname
            # change["parentClass"]=""
            # change["package"]=""
            # change["newClass"]=""
            # change["newClass"]=False
            if mayPackage:
                change["package"]=mayPackage.strip()

            mayClass=className
            if mayClass:
                isnew=line.startswith('+')
                change["newClass"]=isnew
                #需要处理下，因为类名里包含了继承关系 extends AbstractServiceImpl implements ModifiedMethodService 如果是新类，那么需要给标记+父类
                if " extends " in mayClass: #has extends
                    classns=mayClass.split('extends')
                    change["class"]=classns[0].strip() # get classvalue
                    extendN=classns[1].strip()  #extend maybe hav implements
                    if " implements " in extendN :
                        textend=extendN.split('implements')[0].strip()
                        if isnew:  # new method need set value
                            change["parentClass"]=textend
                    elif isnew:
                        change["parentClass"]=extendN
                elif " implements " in mayClass :
                        change["class"]=mayClass.split('implements')[0].strip()
                else:
                     change["class"]=mayClass.rstrip('{')
                    # extendN=classns[1].strip()
                    # if " implements " in extendN :
                    #     textend=extendN.split('implements')[0].strip()
                    #     change["class"]
            maymethod=checkIsMethodNameLine(line)
            if(re.match(r'^[-].+$',line)):#变更的-
                line=line[1:]
                #print maymethod
                if maymethod:
                    result.append(line)
                    if(line not in change.keys()):
                        change[line]="DELETE"
                elif(result and result[-1] not in change.keys()):
                    change[result[-1]]="UPDATE"
            elif(re.match(r'^[+].+$',line)):
                line=line[1:]
                if maymethod:
                    result.append(line)
                    if(line not in change.keys()):
                        change[line]="ADD"
                elif(result and result[-1] not in change.keys()):
                    change[result[-1]]="UPDATE"
            elif maymethod:#看行是否是方法名t
                result.append(line)
        #test
        # for key in change:
        #     print "key:%s,value:" %key
        #     print change[key]
        #     logging.info("key:%s,value:" %key)
        #     logging.info(change[key])
        return change
    except Exception as err:
        print "getChangedMethodRelationInfo Exception:"
        print str(err)
        logging.error("getChangedMethodRelationInfo Exception::%s" %str(err))

#判断源码是否是方法行的正则表达式
def checkIsMethodNameLine(line):
    """
    check  the line is method declare.
    Args:
        line:the check content.
    Return:check result.
    """
    #正则规则：名字、模板、类型
    try:
        namePattern="[a-zA-Z]+\\w*"
        templatePattern="(<[_a-zA-Z]+\\w*(,[a-zA-Z]+\\w*)*>)?"
        typePattern=namePattern+templatePattern
        #参数正则
        argPatternZero=""
        argPatternDynamic="..."
        argPattern=typePattern+" "+namePattern
        argPatternOne=argPattern+"(, ...)?"
        argPatternMulti=argPattern+"(, " +argPattern +")*(, ...)?"
        argsPattern="()"+argPatternOne+"|"+argPatternDynamic+"|" + argPatternOne +"|" +argPatternMulti+")"

        #正则规则：名字、模板、类型
        namePattern=r'[a-zA-Z]+\w*'
        templatePattern=r'(<[_a-zA-Z]+\w*(,[a-zA-Z]+\w*)*>)?'
        typePattern=namePattern+templatePattern
        #参数正则
        argPatternZero=""
        argPatternDynamic="..."
        argPattern=typePattern+" "+namePattern
        argPatternOne=argPattern+r"(, ...)?"
        argPatternMulti=argPattern+r"(, " +argPattern +r")*(, ...)?"
        argsPattern="("+ argPatternOne +"|"+argPatternDynamic+"|" + argPatternOne +"|" +argPatternMulti+")"
        #方法签名的正则
        methodSignaturePattern=r'(public|protected|private|internal)\s+(static\s+)?(final\s+)?'+typePattern+r'\s+'+namePattern+r'('+argsPattern+r')'
        maymethod=re.search(methodSignaturePattern,line)
        if maymethod and re.search(r'^.*[^;]$',line):#(r'^[^=]*[^;]$',line): =号还是可能的，比如给初始值
                    allValue=line.split("(")
                    return len(allValue) > 1
        return None
    except Exception as err:
        print "checkIsMethodNameLine Exception:"
        print str(err)
        logging.error("checkIsMethodNameLine Exception::%s" %str(err))

def setLoggingInfo():
    # logging.basicConfig(filename='logger.log', level=logging.INFO)
    # logging.basicConfig(filename='logger.log',format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)
    logging.basicConfig(filename=('logger_%s.log' %datetime.date.today()),format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)
    fmt = "%(asctime)-15s %(levelname)s %(filename)s %(lineno)d %(process)d %(message)s"
    datefmt = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

def getQasParmsObjects(changeMethodRealtions):
    """
    make qasparmas objects and send datas to qas system.
    Args:
        changeMethods:change method infos.
        return: the file all change methods info.
    """
    try:
        changeMethods=[]
        packname=""
        classname=""
        newClass=False
        parentClass=""
        if changeMethodRealtions.has_key('package'):
            packname=changeMethodRealtions["package"]
        if changeMethodRealtions.has_key('class'):
            classname=changeMethodRealtions["class"]
        if changeMethodRealtions.has_key('newClass'):
            newClass=changeMethodRealtions["newClass"]
        if changeMethodRealtions.has_key('parentClass'):
            parentClass=changeMethodRealtions["parentClass"]
        for key in changeMethodRealtions:
                methodName=""
                parms=""
                if key == "package":
                    packname=changeMethodRealtions[key]
                elif key == "class":
                    classname=changeMethodRealtions[key]
                elif key == "newClass":
                    newClass=changeMethodRealtions[key]
                elif key == "parentClass":
                    parentClass=changeMethodRealtions[key]
                else: #是方法名 的行，需要拆分出方法和参数。
                    methodName=getMethodName(key)
                   # print methodName+":"+changeMethodRealtions[key]
                    parms="(%s)" %getAllParametes(key)
                if methodName :
                    if packname:
                        changeMethods.append(QasModifyMethod(packname,classname,methodName,parms,'',changeMethodRealtions[key],newClass,parentClass))
                    else:
                        changeMethods.append(QasModifyMethod('','',methodName,parms,'',changeMethodRealtions[key],newClass,parentClass))
        ##### get all file and send to qas
        ##### projectName/methodName/packageName/className/params/createdRemark/
        ##### modifiedMethodStatus（UPDATE,ADD,DELETE）/newClass/parentClass
        # if len(changeMethods) > 0:
        #     # datas=QasParamObj("admin","abc@123",str(PROJECTNAME),changeMethods)
        #     datas=QasParamObj(getconfigbyCode('qasuser'),getconfigbyCode('qaspwd'),getconfigbyCode('projectName'),changeMethods)
        #     # datas=QasParamObj(QAS_USER,QAS_PASSWD,PROJECTNAME,changeMethods)
        #     data= json.dumps(datas,default=lambda obj:obj.__dict__, sort_keys=True,indent=4, separators=(',', ': '))
        #     # print data
        #     # print getconfigbyCode('qasurl')
        #     # response=SendChangesToQas(QAS_URL,data)
        #     response=SendChangesToQas(getconfigbyCode('qasurl'),data)
        #     print response.json()
        #     if "True" in str(response.json()):
        #         global changeCount
        #         changeCount+=len(changeMethods)
        return changeMethods
    except Exception as err:
            print "getQasParmsObjects Exception:"
            print err
            logging.error("getQasParmsObjects Exception::%s" %str(err))

#----------------------------------
# dealWithAllChangeMethods: 汇总处理本次版本提交的所有请求变更。
#----------------------------------
def dealWithAllChangeMethodsForGit(allChangeMethodInfos,projectName,newId,newTimeStamp):
    try:
        if len(allChangeMethodInfos) > 0:
            # datas=QasParamObj("admin","abc@123",str(PROJECTNAME),changeMethods)
            datas=QasParamObj(getconfigbyCode('qasuser'),getconfigbyCode('qaspwd'),projectName,allChangeMethodInfos,getconfigbyCode('branchNum'))
            # datas=QasParamObj(QAS_USER,QAS_PASSWD,PROJECTNAME,allChangeMethodInfos)
            data= json.dumps(datas,default=lambda obj:obj.__dict__, sort_keys=True,indent=4, separators=(',', ': '))
            # print "real changed data is :"
            # print data
            # print getconfigbyCode('qasurl')
            # response=SendChangesToQas(QAS_URL,data)
            # logging.info(u"变更是这些内容:%s" %data)
            response=SendChangesToQas(getconfigbyCode('qasurl'),data)
            print response.json()
            if "True" in str(response.json()):
                return len(allChangeMethodInfos)
            else:
                return 0
        return 0
    except Exception as err:
        # print "dealWithAllChangeMethods Exception,version:%s" %str(err)
        logging.error("newId:%s ,dealWithAllChangeMethods Exception:%s" %(newId,str(err)))
        print err
        logging.error("dealWithAllChangeMethods Exception::%s" %str(err))
        return 0

#----------------------------------
# Step9 MakeQasChangeMethodsAndSendtoQas: Use changed methods info to make qasChangeMethondinfo ans send request to qas system.
#----------------------------------
#"methodName":"queryForDeductDispFee","packageName":"com.best.oasis.express.biz.bill.dao","className":"BillDispFeeDAOImpl","modifiedMethodStatus":"UPDATE"}])
class QasModifyMethod(object):
    """
    #"methodName":"queryForDeductDispFee","packageName":"com.best.oasis.express.biz.bill.dao","className":"BillDispFeeDAOImpl","modifiedMethodStatus":"UPDATE"}])
    """
    def __init__(self,packageName,className,methodName,params,createdRemark,modifiedMethodStatus,newClass,parentClass):
        self.methodName=methodName
        self.packageName=packageName
        self.className=className
        self.params=params
        self.createdRemark=createdRemark
        self.status=modifiedMethodStatus
        self.newClass=newClass
        self.parentClass=parentClass

class QasParamObj(object):
    """
    QasParamObj:the parameters for qas interface.
    """
    def __init__(self,username,password,projectName,modifiedMethodVoList,branchNum):
        self.username=username
        self.password=password
        self.projectName=projectName
        self.modifiedMethodVoList=modifiedMethodVoList
        self.branchNum=branchNum
        # self.packageList=packageList 暂时不用这个参数

#----------------------------------
# Step1: Get Config info
#----------------------------------
def getconfigbyCode(code):
    try:
        # conf_ini="./config.ini"
        conf_ini=ConfigUrl#"./config.ini"
        config=ConfigObj(conf_ini,encoding='UTF8')
    except IOError:
        print "config.ini is not found"
        print "Get Config Success2"
        sys.exit()

    try:
        return config['INFO'][code].strip()
    except:
        meg = "%s is not found under section INFO in config.ini." %code
        logging.error("getconfigbyCode Exception::%s" %meg)



def getCSharpNameSpace(linetxt):#for c# namespace
    reFile=re.compile(r'^L.*\s*namespace .*$')
    if reFile.search(linetxt):
        data=linetxt.split('namespace ')
        if data.count > 1:
            return data[1]

def getCSharpClassName(linetxt): #for c# class
    reFile=re.compile(r'^L.*\s*public\s* (partial|abstract)*\s*class .*$')
    if reFile.search(linetxt):
        data=linetxt.split('class')
        if data.count > 1:
            return data[1].strip()

def getMethodName(linetxt): #for c# class
    if checkIsMethodNameLine(linetxt):
        data=linetxt.split('(')
        if data.count > 1:
            m=data[0].split(' ')#按空格分隔，弹出来最后一个就是方法名
            if m.count > 1:
                return m.pop(-1).strip()

def getDiffFileType(filaName):
    """
    getDiffFileType:cs,java,c....
    """
    if filaName:
        data=filaName.split('.')
        if data.count > 1:
            return data.pop(-1).strip()

def getJavaPackageNmae(linetxt):  #for java
    """
    get java package name use regex.
    Args:
        linetxt:check text content.
    Return:
        package name or null
    """
    reFile=re.compile(r'^[+-]?L.*\s*package\s* .*$')  #获取包名正则
    if reFile.search(linetxt):
        data=linetxt.split('package ')
        if data.count > 1:
            return data[1].strip().rstrip(';')


def getJavaClassName(linetxt):#for java
    """
    get java class name use regex.
    Args:
        linetxt:check text content.
    Return:
        class name or null
    """
    reFile=re.compile(r'^[+-]?L.*\s*public\s* (partial|abstract)*\s*class .*$')
    if reFile.search(linetxt):
        data=linetxt.split(' class ')
        if data.count > 1:
            return data[1].strip()

def getAllParametes(linetxt):#for java c# 需要是方法，然后再找 所有参数类型+参数名 拼接成字符串。
    if checkIsMethodNameLine(linetxt):
        data=linetxt.split('(')
        if data.count > 1:
            # m=data[0].split(' ')#按空格分隔，
            # if m.count > 1:
                # print m.pop(-1)
            parms=data[1].strip().split(')')
            return parms[0].strip().lstrip('@RequestBody').strip()

def SaveChangeToTxt(fileName,content):
    """
    add row number to source file text. 增行号到源码中
    Args:
        txtUrl:source file address.
    """
    tmpfold=getconfigbyCode('tmpFolder')
    ftxtUrl='%s_%s' %(tmpfold,fileName)
    try:
        strContent=''
        for i in range(len(content)):
            strContent+="\n"+str(content[i])
        txtfile=open(ftxtUrl,'w')
        txtfile.writelines(strContent)
        txtfile.close()
    except Exception as err:
        print "SaveChangeToTxt Exception:"
        print str(err)
        logging.error("SaveChangeToTxt Exception::%s" %str(err))

def getSvnurl():
    url=getconfigbyCode('svnurl').rstrip("/")
    return "%s/" %url

    #reset version after sendqas data.
def ResetConfigValue(key,value):
    try:
        # conf_ini="./config.ini"
        conf_ini=ConfigUrl
        config=ConfigObj(conf_ini,encoding='UTF8')
        config['INFO'][key]=value
        config.write()
    except IOError:
        print "config.ini is not found"
        logging.error("ResetVersionValue Exception::%s" %meg)
        sys.exit()
#调用QAS方法执行业务操作
def SendChangesToQas(url,parms):
    """
    save changed method info  the qas system.
    Args:
        url:Qas  url.
        parms:data to qas.
    """
    try:
        header={'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36','Referer':getSvnurl(),'Content-Type':'application/json'}
        response=requests.post(url=url,data=parms,headers=header)
        return response
    except Exception as err:
                    print "SendChangesToQas Exception:"
                    print err
                    logging.error("SendChangesToQas Exception::%s" %str(err))
# m=getMethodName("Line 621: L603         UpdateEBillHeader header = bill.getEBillHeader();")#private static final Logger logger = LoggerFactory.getLogger(LocalCacheHelper.class);") #
# print m

