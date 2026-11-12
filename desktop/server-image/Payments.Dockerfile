FROM nahj-server:0.3.1-rc1
USER frappe
WORKDIR /home/frappe/frappe-bench
COPY --chown=1000:1000 payments/ apps/payments/
COPY --chown=1000:1000 payments-constraints.txt /tmp/nahj-payments-constraints.txt
COPY --chown=1000:1000 apps.json /home/frappe/nahj-apps.json
RUN env/bin/python -m ensurepip && \
    env/bin/python -m pip install --no-cache-dir --no-compile \
      --constraint /tmp/nahj-payments-constraints.txt \
      --report /home/frappe/nahj-payments-install.json -e apps/payments && \
    env/bin/python -m pip check && \
    env/bin/python -m pip list --format=json > /home/frappe/nahj-python-packages.json && \
    ln -s /home/frappe/frappe-bench/apps/payments/payments/public /home/frappe/frappe-bench/assets/payments && \
    rm /tmp/nahj-payments-constraints.txt
LABEL io.nahj.payments.commit="9e842a473a8f4ec70a9ff06a3e067d10f98d26ed"
