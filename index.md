---
layout: default
title: Home
---
<h1 class="visually-hidden">{{ site.author.name }}</h1>
<div class="intro">
{%- if site.author.photo != "" %}
<img class="portrait" src="{{ site.author.photo | relative_url }}" alt="Portrait of {{ site.author.name }}" width="160" height="200">
{%- endif %}
<p class="position">{{ site.author.position }}<br>{% for a in site.author.affiliations %}{{ a }}{% unless forloop.last %}<br>{% endunless %}{% endfor %}</p>
</div>

<!-- Draft bio: rewrite freely. -->
I am an Assistant Professor in Responsible Medical AI at the Department of Medical Informatics of Amsterdam UMC and at the Institute for Logic, Language and Computation of the University of Amsterdam. My work aims to make machine learning in healthcare reliable enough to act on: models whose failures can be detected, whose explanations can be checked, and whose predictions support decisions rather than merely correlate with outcomes.

I hold a PhD and an MSc in Mathematical Logic from the ILLC, an MSc in Philosophy of Science from the London School of Economics, and a BA in Philosophy from the University of Milan. I also spent several years at Pacmed as Data Scientist, AI Specialist and Research Lead.

## Research

<!-- Draft list: edit to match how you describe your work. -->
- Out-of-distribution detection and uncertainty estimation for clinical models
- Evaluation of feature attribution methods in explainable AI
- Causal inference for prediction models that inform treatment decisions
- Reinforcement learning and sequential decision-making

{% assign selected = site.data.publications | where: "selected", true -%}
{%- if selected.size > 0 -%}
{%- assign heading = "Selected publications" -%}
{%- else -%}
{%- assign heading = "Recent publications" -%}
{%- assign selected = site.data.publications | slice: 0, 5 -%}
{%- endif %}
## {{ heading }}

<ol class="pubs">
{%- for p in selected %}{% include pub.html pub=p %}{% endfor %}
</ol>
<p class="more"><a href="{{ '/publications/' | relative_url }}">All publications</a></p>

## News

{% assign news = site.data.news | sort: "date" | reverse -%}
<dl class="news">
{%- for item in news limit: site.home_news %}
<dt><time datetime="{{ item.date | date: '%Y-%m-%d' }}">{{ item.date | date: "%B %Y" }}</time></dt>
<dd>{{ item.text | markdownify | remove: '<p>' | remove: '</p>' | strip }}</dd>
{%- endfor %}
</dl>
