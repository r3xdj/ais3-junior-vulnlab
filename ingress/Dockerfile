FROM httpd:2.4.49

COPY httpd.conf /usr/local/apache2/conf/httpd.conf
COPY conf.d/ /usr/local/apache2/conf/conf.d/
COPY html/ /usr/local/apache2/htdocs/
COPY cgi-bin/ /usr/local/apache2/cgi-bin/

# 修正 Windows CRLF，並確保 CGI 可執行
RUN sed -i 's/\r//' /usr/local/apache2/cgi-bin/debug.sh \
    && sed -i 's/\r//' /usr/local/apache2/cgi-bin/test-cgi.sh \
    && chmod +x /usr/local/apache2/cgi-bin/debug.sh \
    && chmod +x /usr/local/apache2/cgi-bin/test-cgi.sh

# 安裝 SSH server, vim, sudo
RUN sed -i 's|deb.debian.org|archive.debian.org|g' /etc/apt/sources.list \
    && sed -i 's|security.debian.org|archive.debian.org|g' /etc/apt/sources.list \
    && apt-get update -o Acquire::Check-Valid-Until=false \
    && apt-get install -y --no-install-recommends openssh-server sudo vim \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd \
    && useradd -m -s /bin/bash opadmin

RUN printf '%s\n' \
    'opadmin ALL=(root) NOPASSWD: /usr/bin/vim' \
    > /etc/sudoers.d/opadmin \
    && chmod 440 /etc/sudoers.d/opadmin \
    && visudo -cf /etc/sudoers.d/opadmin

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 80 22