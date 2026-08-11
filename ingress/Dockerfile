FROM httpd:2.4.49

COPY httpd.conf /usr/local/apache2/conf/httpd.conf

COPY conf.d/ /usr/local/apache2/conf/conf.d/

COPY html/ /usr/local/apache2/htdocs/


RUN sed -i '1c #!/bin/sh' /usr/local/apache2/cgi-bin/test-cgi \
    && chmod +x /usr/local/apache2/cgi-bin/test-cgi

EXPOSE 80
