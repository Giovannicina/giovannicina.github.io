---
layout: default
title: People
permalink: /people/
---
# People
{% unless site.data.people.team or site.data.people.collaborators %}
<p class="lede">No entries yet: add people in <code>_data/people.yml</code>.</p>
{% endunless %}
{% assign team = site.data.people.team -%}
{%- if team and team.size > 0 %}
<h2 id="team">PhDs and Postdocs</h2>

<ul class="people">
{%- for p in team %}{% include person.html person=p %}{% endfor %}
</ul>
{%- endif %}

{% assign collaborators = site.data.people.collaborators -%}
{%- if collaborators and collaborators.size > 0 %}
<h2 id="collaborators">Collaborators</h2>

<ul class="people people-compact">
{%- for p in collaborators %}{% include person.html person=p %}{% endfor %}
</ul>
{%- endif %}
