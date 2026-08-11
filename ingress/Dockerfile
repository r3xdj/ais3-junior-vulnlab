FROM httpd:2.4.49

COPY httpd.conf /usr/local/apache2/conf/httpd.conf
COPY conf.d/ /usr/local/apache2/conf/conf.d/
COPY html/ /usr/local/apache2/htdocs/
COPY cgi-bin/ /usr/local/apache2/cgi-bin/

# 修正 Windows CRLF → Unix LF,並確保執行權限
# debug.sh 和 test-cgi.sh 皆為可執行 CGI
RUN sed -i 's/\r//' /usr/local/apache2/cgi-bin/debug.sh \
    && sed -i 's/\r//' /usr/local/apache2/cgi-bin/test-cgi.sh \
    && chmod +x /usr/local/apache2/cgi-bin/debug.sh \
    && chmod +x /usr/local/apache2/cgi-bin/test-cgi.sh

EXPOSE 80