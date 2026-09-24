---
layout: default
title: CV
permalink: /cv/
---
# Curriculum vitae

{% assign pdf = site.static_files | where: "path", "/assets/cv.pdf" | first -%}
{%- if pdf %}<p class="lede">The full CV is available as a <a href="{{ '/assets/cv.pdf' | relative_url }}">PDF</a>.</p>{% endif %}

<!-- Draft from public sources. Add years in each <dt>. -->
## Positions

<dl class="cv">
<dt>Current</dt>
<dd>Assistant Professor in Responsible Medical AI, Department of Medical Informatics, Amsterdam UMC, and Institute for Logic, Language and Computation, University of Amsterdam</dd>
<dt></dt>
<dd>Data Scientist, AI Specialist and Research Lead, Pacmed, Amsterdam</dd>
</dl>

## Education

<dl class="cv">
<dt></dt>
<dd>PhD in Mathematical Logic, Institute for Logic, Language and Computation, University of Amsterdam</dd>
<dt></dt>
<dd>MSc in Logic, Institute for Logic, Language and Computation, University of Amsterdam</dd>
<dt></dt>
<dd>MSc in Philosophy of Science, London School of Economics and Political Science</dd>
<dt></dt>
<dd>BA in Philosophy, University of Milan</dd>
</dl>
