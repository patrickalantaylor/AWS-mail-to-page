# AWS-mail-to-page
This is a service that integrates Amazon's simple Email Service, with AWS Lambda and AWS S3.

When a mail is recieved by and address which has been configured to get mail on Amazon SES, This script parses the mail and writes the necessary files to S3 to make a full slideshow from the attachments of that mail.

This shows the simplicity, utility and power of AWS services; in this straightforward and understandable Python script, this could make zero web pages for pennies a month, or could make hundreds of thousands for a few hundred dollars. The administrative and development overhead in shifting from 0 mails a month to 100K is literally zero.

On receipt of an email, the AWS Lambda service creates a web page with the email attachments and sends an email back to the sender with and address for that page.

####This uses AWS services: 
### Simple Email Service
### AWS Lambda
### S3
