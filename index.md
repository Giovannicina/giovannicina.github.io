---
layout: default
title: About me
---
# About me

## Background

<!-- Draft: rewrite freely. -->
I am an Assistant Professor in Responsible Medical AI at the Department of Medical Informatics of Amsterdam UMC and at the Institute for Logic, Language and Computation of the University of Amsterdam.

I previously obtained a PhD and a MSc in Mathematical Logic at ILLC, as well as a MSc in Philosophy of Science at London School of Economics and Political Science. My BA is in Philosophy, from the University of Milan. I also spent several years at Pacmed as Data Scientist, AI Specialist and Research Lead.

## Research

In my work I strive to improve the impact and reliability of medical AI applications, with the ultimate goal of making healthcare more accessible and effective.
Current topics include:

- out-of-distribution detection for deployed models;
- evaluation of methods in explainable AI;
- causal inference for ML-driven decision support;
- causal inference for sequential decision-making.

## News

{% assign news = site.data.news | sort: "date" | reverse -%}
<dl class="news">
{%- for item in news limit: site.home_news %}
<dt><time datetime="{{ item.date | date: '%Y-%m-%d' }}">{{ item.date | date: "%B %Y" }}</time></dt>
<dd>{{ item.text | markdownify | remove: '<p>' | remove: '</p>' | strip }}</dd>
{%- endfor %}
</dl>
