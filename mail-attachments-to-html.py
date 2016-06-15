from __future__ import print_function

import os
import sys
import datetime
import json

import mimetypes
import email

import boto3

#the following is the name of the bucket in which the mail is written by SES
S3_MAIL_BUCKET_NAME = 'your-bucket' 
#the following is the name of the prefix (sometimes described as foldername) used when the mail is written to S3 by SES
S3_MAIL_PREFIX = 'prefix-if-you-like' 
#the following is the name of the bucket in which the attachments and html are put
S3_WEB_BUCKET_NAME = 'target-bucket' 
#the following is the prefix under which all digital portfolios will be put.
#The s3 location will then be something like http://s3.amazonaws.com/s3_web_bucket_name/s3_web_prefix/
S3_WEB_BUCKET_PREFIX = 'target-prefix'     
                                    
#this is the name of the bucket which contains the email template                                   
S3_HTML_TEMPLATE_BUCKET = 'your-bucket'
#this is the full key of the html template file which we will use
S3_HTML_TEMPLATE_KEY = 'indextemplate.html'

FROM_EMAIL = 'address-email-comes-from'

print(  "retrieve an email saved in s3, "+ 
        "get the attachements, put the images in a slideshow, "+ 
        "and send an email with the slideshow's url")

s3 = boto3.client('s3')
ses = boto3.client('ses')

def lambda_handler(event, context):
    messageid = event["Records"][0]["ses"]["mail"]["messageId"]
    mailsender = event["Records"][0]["ses"]["mail"]["commonHeaders"]["from"][0]
    if mailsender.find("<") != -1:
        mailsenderlabel = mailsender[mailsender.index("<") + 1:mailsender.rindex(">")]
    else:
        mailsenderlabel = mailsender
    mailsenderlabel = mailsenderlabel.split('@')[0].split('.')[0]
    mailobjectkey = S3_MAIL_PREFIX + messageid
    mailmetadata = s3.get_object(Bucket=S3_MAIL_BUCKET_NAME, Key=mailobjectkey)
    mailobject = mailmetadata['Body']
    mailsubject = event["Records"][0]["ses"]["mail"]["commonHeaders"]["subject"]
    
    pageid = messageid[0:5]
    pagekey = os.path.join(S3_WEB_BUCKET_PREFIX,mailsenderlabel,pageid)
    pagekeyisunique = False
    pagekeyuniqueaddendum = 0
    while not (pagekeyisunique):
        duplicatepagekeycheck = s3.list_objects(Bucket=S3_WEB_BUCKET_NAME, Prefix=pagekey)
        if 'Contents' in duplicatepagekeycheck.keys():
            print("dupe")
            pageid = pageid[0:5]+str(pagekeyuniqueaddendum)
            pagekey = os.path.join(S3_WEB_BUCKET_PREFIX,mailsenderlabel,pageid)
            pagekeyuniqueaddendum += 1
        else:
            pagekeyisunique = True
    
    foliobucketprefix = os.path.join(   S3_WEB_BUCKET_PREFIX, 
                                        mailsenderlabel, 
                                        pageid)
    print("page will be saved with key prefix: " + foliobucketprefix)

    templatefile = s3.get_object(   Bucket=S3_HTML_TEMPLATE_BUCKET , 
                                    Key=S3_HTML_TEMPLATE_KEY
                                    )['Body'].read()
    
    emailmessage = email.message_from_file(mailobject)
    imagesincluded = False
    for i,part in enumerate(emailmessage.walk(),1):
        if part.get_content_maintype() == 'image':
            # if we need to synthesize a filename # ext = mimetypes.guess_extension(part.get_content_type())
            filename=part.get_filename()
            fileURL = os.path.join("http://", 
                                    S3_WEB_BUCKET_NAME, 
                                    foliobucketprefix, 
                                    filename)
            replacementstring = ("<!--imagecodehere--> \n" +
                                "<img class=\"mySlides\" src=\"" + 
                                fileURL + 
                                "\" style=\"width:100%\" onclick=\"plusDivs(1)\">\n")
            templatefile = templatefile.replace('<!--imagecodehere-->', 
                                                replacementstring)
            thisattachment = part.get_payload(decode=True)
            s3.put_object(  Body=thisattachment, 
                            Bucket=S3_WEB_BUCKET_NAME, 
                            Key=os.path.join(foliobucketprefix, filename), 
                            ContentType=part.get_content_type(), 
                            ACL='public-read')
            imagesincluded = True
    if imagesincluded:
        datestring = (datetime.datetime.now().strftime("%B %d, %Y"))
        if mailsubject[0:7].lower() == "digital":
            slideshowtext = mailsubject + " " + datestring
        else:
            slideshowtext = datestring 
        slideshowmarkup = "<h2 class=\"w3-center\">" + slideshowtext + "</h2>"
        templatefile = templatefile.replace(    '<!-- slideshowText -->', 
                                                slideshowmarkup)
        templatefile = templatefile.replace(    '<!-- titleText -->', 
                                                slideshowtext)
        response = s3.put_object(  Body=templatefile, 
                        Bucket=S3_WEB_BUCKET_NAME, 
                        Key=os.path.join(foliobucketprefix, 'index.html'), 
                        ContentType='text/html', 
                        ACL='public-read')
        print(response)
        response = ses.send_email(  Source=FROM_EMAIL,
                                    Destination={'ToAddresses': [mailsender]},
                                    Message={
                                            'Subject': 
                                                {
                                                'Data': 'Your page has been built',
                                                'Charset': 'UTF-8'
                                                },
                                            'Body': 
                                                {
                                                'Text': 
                                                    {
                                                    'Data': os.path.join("http://", S3_WEB_BUCKET_NAME, foliobucketprefix) ,
                                                    'Charset': 'UTF-8'
                                                    }
                                                }
                                            }
                                    )
        print(str(response))
    else:
        response = ses.send_email(  Source=FROM_EMAIL,
                                    Destination={'ToAddresses': [mailsender]},
                                    Message={
                                            'Subject': 
                                                {
                                                'Data': 'there was a problem with your request',
                                                'Charset': 'UTF-8'
                                                },
                                            'Body': 
                                                {
                                                'Text': 
                                                    {
                                                    'Data': 'No images were detected attached to your email' ,
                                                    'Charset': 'UTF-8'
                                                    }
                                                }
                                            }
                                    )
        print(str(response))
    return 0
