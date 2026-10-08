---
layout: default
title: About me
---
# About me

## Background

<!-- Draft: rewrite freely. -->
I am an Assistant Professor in Responsible Medical AI at the [Department of Medical Informatics](https://kik.amsterdamumc.org) of the Amsterdam University Medical Center and at the [Institute for Logic, Language and Computation](https://www.illc.uva.nl) of the University of Amsterdam. My team is embedded in the [Methods in Medical Informatics](https://kik.amsterdamumc.org/methods-in-medical-informatics/) group.

I previously obtained a PhD and a MSc in Mathematical Logic at ILLC, as well as a MSc in Philosophy of Science at [London School of Economics and Political Science](https://www.lse.ac.uk). My BA is in Philosophy, from the [University of Milan](https://www.unimi.it/en). I also spent several years at [Pacmed](https://www.pacmed.ai/en) as Data Scientist, AI Specialist and Research Lead.

I am a Member of [ELLIS](https://ellis.eu) and an organizer of the [Amsterdam Causality Meetings](https://amscausality.github.io).

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
