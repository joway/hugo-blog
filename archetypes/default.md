---
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date | time.Format "2006-01-02" }}
categories: ["Tech"]
draft: true
---
