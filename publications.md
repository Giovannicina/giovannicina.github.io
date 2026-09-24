---
layout: default
title: Publications
permalink: /publications/
---
# Publications

<p class="lede">Also listed on <a href="https://dblp.org/pid/{{ site.publications.dblp }}.html">DBLP</a>, <a href="https://orcid.org/{{ site.publications.orcid }}">ORCID</a> and <a href="{{ site.links[0].url }}">Google Scholar</a>. An asterisk (*) marks equal contribution.</p>

{% assign years = site.data.publications | group_by: "year" -%}
{%- for y in years %}
<section class="year" aria-labelledby="y{{ y.name }}">
<h2 id="y{{ y.name }}">{{ y.name }}</h2>
<ol class="pubs">
{%- for p in y.items %}{% include pub.html pub=p %}{% endfor %}
</ol>
</section>
{%- endfor %}
