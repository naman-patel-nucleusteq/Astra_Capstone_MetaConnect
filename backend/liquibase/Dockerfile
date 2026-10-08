FROM liquibase/liquibase:5.0.4

RUN lpm add postgresql --global

COPY db.changelog-master.yaml /liquibase/changelog/db.changelog-master.yaml
COPY changesets /liquibase/changelog/changesets