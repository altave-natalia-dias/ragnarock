# UOL — RAG leads (webmail XSS / email read / ATO)
- Mail.ru stored XSS (sanitizer bypass): https://www.seekurity.com/blog/general/stored-xss-in-the-heart-of-the-russian-email-provider-giant-mail-ru/
- Outlook Web stored XSS: https://medium.com/@elmrhassel/xss-stored-on-outlook-web-outlook-android-app-ad4bd46b8823
- Protonmail stored XSS: https://medium.com/@ChandSingh/protonmail-xss-stored-b733031ac3b5
- Yahoo stored XSS: https://medium.com/@TheShahzada/stored-xss-in-yahoo-b0878ecc97e2
- MIME-sniffing XSS: https://www.komodosec.com/post/mime-sniffing-xss
- Email address flexibility (parser differential → ATO): https://modzero.com/en/blog/beyond_the_at_symbol/
## TTP focus: HTML email sanitizer bypass (svg/math/style/mXSS/mutation), MIME confusion on attachments, address parser differentials.
