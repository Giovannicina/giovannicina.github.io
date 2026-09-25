---
layout: default
title: About me
---
# About me

## Background

<!-- Draft: rewrite freely. -->
I am an Assistant Professor in Responsible Medical AI at the Department of Medical Informatics of Amsterdam UMC and at the Institute for Logic, Language and Computation of the University of Amsterdam.

I hold a PhD and an MSc in Mathematical Logic from the ILLC, an MSc in Philosophy of Science from the London School of Economics, and a BA in Philosophy from the University of Milan. I also spent several years at Pacmed as Data Scientist, AI Specialist and Research Lead.

## Research

<!-- Draft: edit to match how you describe your work. -->
My work aims to make machine learning in healthcare reliable enough to act on. Current topics include:

- out-of-distribution detection and uncertainty estimation for clinical models;
- evaluation of feature attribution methods in explainable AI;
- causal inference for prediction models that inform treatment decisions;
- reinforcement learning and sequential decision-making.

## News

{% assign news = site.data.news | sort: "date" | reverse -%}
<dl class="news">
{%- for item in news limit: site.home_news %}
<dt><time datetime="{{ item.date | date: '%Y-%m-%d' }}">{{ item.date | date: "%B %Y" }}</time></dt>
<dd>{{ item.text | markdownify | remove: '<p>' | remove: '</p>' | strip }}</dd>
{%- endfor %}
</dl>
