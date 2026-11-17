"""The help of every page, in plain words.

The help banners were written for a reader who already knew the subject :
"This page presents the selected risk criteria set with its likelihood scale",
"ISO Harmonized Structure §4.1", "CIA levels", "the GRC framework". A newcomer
learnt nothing from them. Each one now says what the thing is in one sentence
(its title), gives an example, and says what to do first or what to watch
(docs/sdk/usability-standard.md, rule W4), in the words of the glossary
(docs/brand/glossary.md).

Thirteen pages that had a help tag and no text, or no help at all, gain one :
the incident registers, the contracts, the certificates, the nonconformities,
the management reviews, the reports and the lifecycles.

A help an administrator rewrote is left alone : a row is replaced only while
it still holds the text a previous migration shipped (recognised by its
fingerprint), and a row that does not exist is created. The five rows no page
shows any more are removed under the same condition.

Reversing leaves the texts where they are : the previous wording is nothing
the earlier code depends on, and it is not kept here.
"""

import hashlib

from django.db import migrations

# key -> ((English title, English body), (French title, French body))
HELP = {
    "home": (
        ("Your dashboard : what needs you today",
         "The figures that sum up where you stand, what is late or due soon, and the first things to deal with. Every figure is a link to the records behind it. Rearrange the tiles to keep the ones that serve you."),
        ("Votre tableau de bord : ce qui a besoin de vous aujourd'hui",
         "Les chiffres qui résument où vous en êtes, ce qui est en retard ou arrive à échéance, et les premières choses à traiter. Chaque chiffre est un lien vers les fiches correspondantes. Réorganisez les tuiles pour garder celles qui vous servent."),
    ),
    "accounts.user_list": (
        ("One account for each person who uses the application",
         "A user signs in with their email address. What they may see and do comes from the groups you put them in, and from the scopes they are given. To bring a colleague in, create their account and choose their group."),
        ("Un compte pour chaque personne qui utilise l'application",
         "Un utilisateur se connecte avec son adresse e-mail. Ce qu'il peut voir et faire dépend des groupes où vous le placez, et des périmètres qui lui sont attribués. Pour faire entrer un collègue, créez son compte et choisissez son groupe."),
    ),
    "accounts.user_detail": (
        ("Everything about one account",
         "Who this person is, the groups they belong to, what they may do as a result, and their recent sign-ins. Change their groups here to give or withdraw rights. When the person leaves, deactivate the account rather than delete it, so the history keeps their name."),
        ("Tout ce qui concerne un compte",
         "Qui est cette personne, les groupes auxquels elle appartient, ce qu'elle peut faire en conséquence, et ses dernières connexions. Modifiez ses groupes ici pour donner ou retirer des droits. Au départ de la personne, désactivez le compte plutôt que de le supprimer, pour que l'historique garde son nom."),
    ),
    "accounts.group_list": (
        ("A group gives the same rights to several people",
         "Rather than setting rights person by person, you put people in a group. The groups delivered with the application cover the usual cases, from reading only to full administration, and cannot be changed. Create your own when none fits, for an outside auditor for example."),
        ("Un groupe donne les mêmes droits à plusieurs personnes",
         "Plutôt que de régler les droits personne par personne, vous placez les personnes dans un groupe. Les groupes livrés avec l'application couvrent les cas courants, de la simple lecture à l'administration complète, et ne se modifient pas. Créez le vôtre quand aucun ne convient, pour un auditeur externe par exemple."),
    ),
    "accounts.group_detail": (
        ("What this group allows, and who is in it",
         "The permissions of the group and its members. Adding someone here gives them every right listed; removing them takes those rights away at once. A group delivered with the application shows its permissions but cannot be edited."),
        ("Ce que ce groupe autorise, et qui en fait partie",
         "Les permissions du groupe et ses membres. Ajouter une personne ici lui donne tous les droits listés ; la retirer les lui enlève aussitôt. Un groupe livré avec l'application montre ses permissions mais ne se modifie pas."),
    ),
    "accounts.permission_list": (
        ("A permission is one thing a person may do",
         "Reading the risks, creating a supplier, approving a document : each is a permission. A permission is never given to a person directly, only through a group. This page lists them all, to see which groups carry which."),
        ("Une permission est une chose qu'une personne peut faire",
         "Lire les risques, créer un fournisseur, approuver un document : chacune est une permission. Une permission ne se donne jamais directement à une personne, seulement par un groupe. Cette page les liste toutes, pour voir quels groupes portent lesquelles."),
    ),
    "accounts.access_log_list": (
        ("Who signed in, when, and from where",
         "Every sign-in, failed attempt, sign-out, lockout and password change is recorded here, and cannot be edited. Look here when an account behaves oddly : several failures in a row from an unknown address deserve a question."),
        ("Qui s'est connecté, quand, et d'où",
         "Chaque connexion, tentative échouée, déconnexion, blocage de compte et changement de mot de passe est consigné ici, et ne peut pas être modifié. Regardez ici quand un compte se comporte bizarrement : plusieurs échecs de suite depuis une adresse inconnue méritent une question."),
    ),
    "accounts.action_log_list": (
        ("Who changed what, and when",
         "Every creation, change, deletion and move through a lifecycle is recorded here with its author, and cannot be edited. It is what lets you answer an auditor who asks who approved a record."),
        ("Qui a modifié quoi, et quand",
         "Chaque création, modification, suppression et changement d'étape est consigné ici avec son auteur, et ne peut pas être modifié. C'est ce qui permet de répondre à un auditeur qui demande qui a approuvé une fiche."),
    ),
    "context.scope_list": (
        ("A scope says what your security work covers",
         "The whole company, one site or one activity. Every other record (assets, risks, frameworks) is filed under a scope, and each user sees the records of the scopes they are given. Start with one scope for the whole organisation; split it later if you need to (ISO 27001, clause 4.3)."),
        ("Un périmètre dit ce que couvre votre démarche de sécurité",
         "Toute l'entreprise, un site ou une activité. Toutes les autres fiches (biens, risques, référentiels) se rangent sous un périmètre, et chaque utilisateur voit les fiches des périmètres qui lui sont attribués. Commencez par un seul périmètre pour toute l'organisation ; vous le découperez plus tard si besoin (ISO 27001, chapitre 4.3)."),
    ),
    "context.scope_detail": (
        ("A scope is completed on this page",
         "It was created with its name. The list at the top says what it still needs, and each card has its own Edit button. Before it can be submitted for validation, a scope must say where it stops and name at least one manager."),
        ("Un périmètre se complète sur cette page",
         "Il a été créé avec son nom. La liste en haut de page indique ce qui lui manque, et chaque carte a son propre bouton Modifier. Avant d'être soumis à validation, un périmètre doit indiquer où il s'arrête et désigner au moins un responsable."),
    ),
    "context.site_list": (
        ("A site is a place where you work or keep your equipment",
         "Head office, a branch, a data centre, a factory. Listing your sites lets you say where each asset is, and see what a physical event, a fire or a break-in, would affect."),
        ("Un site est un lieu où vous travaillez ou gardez vos équipements",
         "Le siège, une agence, un centre de données, une usine. Lister vos sites permet de dire où se trouve chaque bien, et de voir ce qu'un événement physique, un incendie ou une effraction, toucherait."),
    ),
    "context.issue_list": (
        ("An issue is a fact that weighs on your security",
         "Inside the organisation : fast growth, a move to the cloud, a high turnover of staff. Outside : a new regulation, a tense market, a wave of attacks in your sector. List the few that really count; your objectives and your risks will answer them (ISO 27001, clause 4.1)."),
        ("Un enjeu est un fait qui pèse sur votre sécurité",
         "Dans l'organisation : une croissance rapide, un passage au cloud, un fort renouvellement des équipes. Autour d'elle : une nouvelle réglementation, un marché tendu, une vague d'attaques dans votre secteur. Listez les quelques-uns qui comptent vraiment ; vos objectifs et vos risques y répondront (ISO 27001, chapitre 4.1)."),
    ),
    "context.issue_detail": (
        ("One issue, and what answers it",
         "Whether it comes from inside or outside, how much it weighs, and the stakeholders and objectives linked to it. An issue nobody acts on is only a remark : link it to an objective or to a risk."),
        ("Un enjeu, et ce qui y répond",
         "S'il vient de l'intérieur ou de l'extérieur, son poids, et les parties intéressées et les objectifs qui lui sont liés. Un enjeu sur lequel personne n'agit n'est qu'une remarque : reliez-le à un objectif ou à un risque."),
    ),
    "context.stakeholder_list": (
        ("A stakeholder is someone who expects something of your security",
         "A client who wants its data kept safe, a regulator, your insurer, your staff. Note who they are and what each one expects : these expectations are requirements you will have to show you meet (ISO 27001, clause 4.2)."),
        ("Une partie intéressée est quelqu'un qui attend quelque chose de votre sécurité",
         "Un client qui veut ses données protégées, un régulateur, votre assureur, vos collaborateurs. Notez qui elles sont et ce que chacune attend : ces attentes sont des exigences dont vous devrez montrer que vous y répondez (ISO 27001, chapitre 4.2)."),
    ),
    "context.stakeholder_detail": (
        ("One stakeholder, and what it expects",
         "Who it is, how much it weighs on you and how much it cares, and its expectations one by one. Review the list when the relationship changes : a new contract often brings new expectations."),
        ("Une partie intéressée, et ce qu'elle attend",
         "Qui elle est, son influence sur vous et son intérêt pour votre sécurité, et ses attentes une par une. Revoyez la liste quand la relation change : un nouveau contrat apporte souvent de nouvelles attentes."),
    ),
    "context.objective_list": (
        ("An objective is a measurable aim of your security work",
         "Train every newcomer within a month; restore any server in under four hours. Give each objective an owner, a date and a figure that says whether it is reached : an aim nobody can measure cannot be shown to an auditor (ISO 27001, clause 6.2)."),
        ("Un objectif est un but mesurable de votre démarche de sécurité",
         "Former chaque nouvel arrivant dans le mois ; restaurer n'importe quel serveur en moins de quatre heures. Donnez à chaque objectif un propriétaire, une date et un chiffre qui dit s'il est atteint : un but que personne ne peut mesurer ne se montre pas à un auditeur (ISO 27001, chapitre 6.2)."),
    ),
    "context.objective_detail": (
        ("One objective, and how far it has got",
         "Its target, its current value, who answers for it and by when. Update the current value each time you measure it : the progress shown everywhere else is read from here."),
        ("Un objectif, et où il en est",
         "Sa cible, sa valeur actuelle, qui en répond et pour quand. Mettez à jour la valeur actuelle à chaque relevé : l'avancement affiché partout ailleurs est lu ici."),
    ),
    "context.swot_list": (
        ("A SWOT analysis is a four-box picture of where you stand",
         "Strengths and weaknesses are yours; opportunities and threats come from outside. Filling the four boxes with your team is a quick way to find your issues and to choose your objectives."),
        ("Une analyse SWOT est un tableau en quatre cases de votre situation",
         "Forces et faiblesses sont les vôtres ; opportunités et menaces viennent de l'extérieur. Le sigle reprend ces quatre mots en anglais. Remplir les quatre cases avec votre équipe est un moyen rapide de trouver vos enjeux et de choisir vos objectifs."),
    ),
    "context.swot_detail": (
        ("One analysis, box by box",
         "Add what you see in each box, then draw strategies from them : use a strength to seize an opportunity, fix a weakness before a threat exploits it. Keep each line short and concrete."),
        ("Une analyse, case par case",
         "Ajoutez ce que vous voyez dans chaque case, puis tirez-en des stratégies : utiliser une force pour saisir une opportunité, corriger une faiblesse avant qu'une menace ne l'exploite. Gardez chaque ligne courte et concrète."),
    ),
    "context.role_list": (
        ("A role says who does what for security",
         "Security officer, data protection officer, person in charge of the backups : a role is a function, with its responsibilities, that you then give to a person. A role that must be filled and that nobody holds is flagged (ISO 27001, clause 5.3)."),
        ("Un rôle dit qui fait quoi pour la sécurité",
         "Responsable de la sécurité, délégué à la protection des données, personne chargée des sauvegardes : un rôle est une fonction, avec ses responsabilités, que vous confiez ensuite à une personne. Un rôle obligatoire que personne ne tient est signalé (ISO 27001, chapitre 5.3)."),
    ),
    "context.role_detail": (
        ("One role, its responsibilities and who holds it",
         "For each responsibility you say how the role is involved : it does the work, answers for the result, is asked before, or is told after. Name at least one person : a role held by nobody protects nothing."),
        ("Un rôle, ses responsabilités et qui le tient",
         "Pour chaque responsabilité, vous dites comment le rôle est impliqué : il réalise le travail, répond du résultat, est consulté avant, ou est informé après. Désignez au moins une personne : un rôle que personne ne tient ne protège rien."),
    ),
    "context.activity_list": (
        ("An activity is something the organisation does as part of its business",
         "Invoicing, recruiting, manufacturing, customer support. Listing your activities, and how critical each one is, is the shortest way to your essential assets : what must each activity never lose ?"),
        ("Une activité est ce que l'organisation fait dans le cadre de son métier",
         "Facturer, recruter, fabriquer, assurer le support client. Lister vos activités, avec la criticité de chacune, est le plus court chemin vers vos biens essentiels : que ne doit jamais perdre chacune d'elles ?"),
    ),
    "context.activity_detail": (
        ("One activity, and what it relies on",
         "What it is, how critical it is, who answers for it and the essential assets it uses. A critical activity with no owner is flagged : somebody must be able to say what it needs."),
        ("Une activité, et ce sur quoi elle repose",
         "Ce qu'elle est, sa criticité, qui en répond et les biens essentiels qu'elle utilise. Une activité critique sans propriétaire est signalée : quelqu'un doit pouvoir dire ce dont elle a besoin."),
    ),
    "context.indicator_list": (
        ("An indicator is a figure you follow over time",
         "The share of laptops encrypted, the time taken to close an incident, the rate of compliance with a framework. Give each one an expected level and a threshold below which you react. Some are calculated for you from the records of the application."),
        ("Un indicateur est un chiffre que vous suivez dans le temps",
         "La part des ordinateurs portables chiffrés, le temps mis à clore un incident, le taux de conformité à un référentiel. Donnez à chacun un niveau attendu et un seuil en dessous duquel vous réagissez. Certains sont calculés pour vous à partir des fiches de l'application."),
    ),
    "context.indicator_detail": (
        ("One indicator, and its measurements",
         "Its current value against the level you expect, its thresholds and every measurement taken. Record a measurement at the frequency shown : a figure that is never refreshed tells nothing."),
        ("Un indicateur, et ses relevés",
         "Sa valeur actuelle face au niveau attendu, ses seuils et chaque relevé effectué. Enregistrez un relevé à la fréquence indiquée : un chiffre jamais rafraîchi ne dit rien."),
    ),
    "context.tag_list": (
        ("A tag is a free word you put on records to find them again",
         "Critical infrastructure, project Alpha, to review in June. Create the tags you need, give each one a colour, then filter any list by tag. Keep them few : fifty tags sort nothing."),
        ("Une étiquette est un mot libre que vous posez sur des fiches pour les retrouver",
         "Infrastructure critique, projet Alpha, à revoir en juin. Créez les étiquettes dont vous avez besoin, donnez une couleur à chacune, puis filtrez n'importe quelle liste par étiquette. Gardez-en peu : cinquante étiquettes ne trient rien."),
    ),
    "reports.management_review_list": (
        ("A management review is the meeting where the management looks at security",
         "Once or twice a year, the management goes through what happened : audits, incidents, risks, objectives. It decides what changes, and each decision gets an owner and a date. Plan the next one, and the application gathers the figures to present (ISO 27001, clause 9.3)."),
        ("Une revue de direction est la réunion où la direction examine la sécurité",
         "Une ou deux fois par an, la direction passe en revue ce qui s'est produit : audits, incidents, risques, objectifs. Elle décide de ce qui change, et chaque décision reçoit un propriétaire et une date. Planifiez la prochaine, et l'application rassemble les chiffres à présenter (ISO 27001, chapitre 9.3)."),
    ),
    "reports.report_list": (
        ("A report is a document the application writes from your records",
         "The statement of applicability, an audit report, the risk register. Each one is generated at a given date and kept as it was : what you showed an auditor in March can still be shown in December."),
        ("Un rapport est un document que l'application rédige à partir de vos fiches",
         "La déclaration d'applicabilité, un rapport d'audit, le registre des risques. Chacun est généré à une date donnée et conservé tel quel : ce que vous avez montré à un auditeur en mars peut encore être montré en décembre."),
    ),
    "assets.essential_asset_list": (
        ("An essential asset is what the business cannot do without",
         "A piece of information you hold (the customer file) or an activity you run (payroll). For each one you say how much harm it would do if it were disclosed, wrong or out of reach : its security needs, which carry over to the systems it relies on. Start with the five or six that matter most."),
        ("Un bien essentiel est ce dont l'activité ne peut pas se passer",
         "Une information que vous détenez (le fichier clients) ou une activité que vous menez (la paie). Pour chacun, vous indiquez la gravité des conséquences s'il était divulgué, faux ou inaccessible : ses besoins de sécurité, qui se reportent sur les systèmes dont il dépend. Commencez par les cinq ou six qui comptent le plus."),
    ),
    "assets.essential_asset_detail": (
        ("An essential asset is completed on this page",
         "It was created with its name and who answers for it. The list at the top says what it still needs, and each card has its own Edit button. Its security needs (confidentiality, integrity, availability) must be assessed before it can become active."),
        ("Un bien essentiel se complète sur cette page",
         "Il a été créé avec son nom et la personne qui en répond. La liste en haut de page indique ce qui lui manque, et chaque carte a son propre bouton Modifier. Ses besoins de sécurité (disponibilité, intégrité, confidentialité) doivent être évalués avant qu'il puisse passer à l'étape Actif."),
    ),
    "assets.support_asset_list": (
        ("A support asset is what your essential assets run on",
         "A server, an application, a network, premises, a team, a service bought from a supplier. It takes the security needs of the essential assets that depend on it, the highest of each. Two things are flagged for you : an asset no essential asset uses, and one that has reached its end of life."),
        ("Un bien support est ce sur quoi reposent vos biens essentiels",
         "Un serveur, une application, un réseau, des locaux, une équipe, un service acheté à un fournisseur. Il reçoit les besoins de sécurité des biens essentiels qui en dépendent, le plus élevé de chacun. Deux situations vous sont signalées : un bien qu'aucun bien essentiel n'utilise, et un bien arrivé en fin de vie."),
    ),
    "assets.support_asset_detail": (
        ("Everything about one support asset",
         "What it is, who looks after it, where it stands in its life, and the security needs it inherits from the essential assets that rely on it. Link it to those essential assets through the dependencies : without that link, nothing says why it deserves protection."),
        ("Tout ce qui concerne un bien support",
         "Ce qu'il est, qui s'en occupe, où il en est de sa vie, et les besoins de sécurité qu'il hérite des biens essentiels qui s'appuient sur lui. Reliez-le à ces biens essentiels par les dépendances : sans ce lien, rien ne dit pourquoi il mérite d'être protégé."),
    ),
    "assets.dependency_list": (
        ("A dependency says that one asset needs another to work",
         "Payroll needs the HR application, which needs its server. Draw these links and the application tells you two things : what an essential asset really relies on, and the single points of failure, the assets whose breakdown stops everything because nothing replaces them."),
        ("Une dépendance dit qu'un bien a besoin d'un autre pour fonctionner",
         "La paie a besoin de l'application RH, qui a besoin de son serveur. Tracez ces liens et l'application vous dit deux choses : ce sur quoi un bien essentiel repose vraiment, et les points de défaillance unique, ces biens dont la panne arrête tout parce que rien ne les remplace."),
    ),
    "assets.supplier_dependency_list": (
        ("Which of your assets depend on which supplier",
         "Your website depends on its hosting company, your payroll on the publisher of the HR software. Recording these links shows what stops when a supplier fails, and which supplier has become a single point of failure because no other can take over."),
        ("Lesquels de vos biens dépendent de quel fournisseur",
         "Votre site web dépend de son hébergeur, votre paie de l'éditeur du logiciel RH. Enregistrer ces liens montre ce qui s'arrête quand un fournisseur fait défaut, et quel fournisseur est devenu un point de défaillance unique parce qu'aucun autre ne peut prendre le relais."),
    ),
    "assets.site_asset_dependency_list": (
        ("Which assets are kept at which site",
         "The servers in the computer room in Lyon, the archives at head office. This is what tells you what a fire, a flood or a power cut at one site would take with it."),
        ("Quels biens se trouvent sur quel site",
         "Les serveurs dans la salle informatique de Lyon, les archives au siège. C'est ce qui vous dit ce qu'un incendie, une inondation ou une coupure de courant sur un site emporterait avec lui."),
    ),
    "assets.site_supplier_dependency_list": (
        ("Which supplier each site relies on",
         "The electricity provider of the factory, the internet access of each office, the company that guards the premises. Record them to see what a site loses when one of them fails."),
        ("De quel fournisseur dépend chaque site",
         "Le fournisseur d'électricité de l'usine, l'accès internet de chaque bureau, la société qui garde les locaux. Enregistrez-les pour voir ce qu'un site perd quand l'un d'eux fait défaut."),
    ),
    "assets.site_detail": (
        ("Everything about one site",
         "Its address and how critical it is, the support assets kept there and the suppliers it relies on. Read it as the answer to one question : what would you lose if this site were out of reach tomorrow ?"),
        ("Tout ce qui concerne un site",
         "Son adresse et sa criticité, les biens supports qui s'y trouvent et les fournisseurs dont il dépend. Lisez-la comme la réponse à une question : que perdriez-vous si ce site était inaccessible demain ?"),
    ),
    "assets.group_list": (
        ("A group gathers support assets that go together",
         "All the laptops of the sales team, the servers of one room, the applications of one publisher. Assess a risk or apply a control once for the group, instead of repeating it asset by asset."),
        ("Un groupe rassemble des biens supports qui vont ensemble",
         "Tous les ordinateurs portables de l'équipe commerciale, les serveurs d'une même salle, les applications d'un même éditeur. Appréciez un risque ou appliquez une mesure une fois pour le groupe, au lieu de le répéter bien par bien."),
    ),
    "assets.group_detail": (
        ("What this group gathers",
         "The kind of group it is and the support assets it holds. Add or remove assets here as your inventory changes."),
        ("Ce que ce groupe rassemble",
         "Le type de groupe et les biens supports qu'il contient. Ajoutez ou retirez des biens ici à mesure que votre inventaire évolue."),
    ),
    "assets.supplier_list": (
        ("A supplier is an outside organisation you depend on",
         "Your hosting company, the publisher of your accounting software, the firm that maintains your network. For each one you record how critical it is, its contracts, and what you require of it. Start with those whose failure would stop an essential asset."),
        ("Un fournisseur est une organisation extérieure dont vous dépendez",
         "Votre hébergeur, l'éditeur de votre logiciel de comptabilité, la société qui entretient votre réseau. Pour chacun, vous notez sa criticité, ses contrats et ce que vous exigez de lui. Commencez par ceux dont la défaillance arrêterait un bien essentiel."),
    ),
    "assets.supplier_detail": (
        ("Everything you know about one supplier",
         "Who to call, how critical it is, its contracts, what you require of it and whether it complies. Review it at the date shown : a supplier that was sound two years ago may not be today."),
        ("Tout ce que vous savez d'un fournisseur",
         "Qui appeler, sa criticité, ses contrats, ce que vous exigez de lui et s'il s'y conforme. Revoyez sa fiche à la date indiquée : un fournisseur solide il y a deux ans ne l'est peut-être plus aujourd'hui."),
    ),
    "assets.supplier_type_list": (
        ("A supplier type says what you require of a kind of supplier",
         "Hosting company, software publisher, consultant : each type carries the requirements you ask of every supplier of that kind, a security certificate for a hosting company for example. A new supplier of the type receives them without retyping."),
        ("Un type de fournisseur dit ce que vous exigez d'une catégorie de fournisseurs",
         "Hébergeur, éditeur de logiciel, consultant : chaque type porte les exigences que vous demandez à tout fournisseur de cette catégorie, un certificat de sécurité pour un hébergeur par exemple. Un nouveau fournisseur du type les reçoit sans ressaisie."),
    ),
    "assets.supplier_type_detail": (
        ("What you require of every supplier of this type",
         "The requirements listed here are given to each supplier of this type. Keep the list short : each line is something you will have to check with every one of them."),
        ("Ce que vous exigez de tout fournisseur de ce type",
         "Les exigences listées ici sont données à chaque fournisseur de ce type. Gardez la liste courte : chaque ligne est une chose que vous devrez vérifier auprès de chacun d'eux."),
    ),
    "assets.supplier_requirement_detail": (
        ("One thing you require of this supplier",
         "What you asked, whether the supplier meets it, and the evidence that shows it : a certificate, a signed clause, a report. Review it at the date shown and record each review, so that you can show the supplier was followed."),
        ("Une chose que vous exigez de ce fournisseur",
         "Ce que vous avez demandé, si le fournisseur y répond, et la preuve qui le montre : un certificat, une clause signée, un rapport. Revoyez-la à la date indiquée et consignez chaque revue, pour pouvoir montrer que le fournisseur a été suivi."),
    ),
    "assets.contract_list": (
        ("The contracts that bind you to your suppliers and your clients",
         "What was signed, with whom, from when to when, and its amendments. A supplier contract that has run out is flagged on the dashboard : a service you depend on should not run without one."),
        ("Les contrats qui vous lient à vos fournisseurs et à vos clients",
         "Ce qui a été signé, avec qui, de quand à quand, et ses avenants. Un contrat fournisseur arrivé à échéance est signalé sur le tableau de bord : un service dont vous dépendez ne devrait pas fonctionner sans contrat."),
    ),
    "assets.certificate_list": (
        ("A certificate proves that an auditor recognised your work",
         "An ISO 27001 certificate, for example : which framework it covers, which part of the organisation, who issued it and until when. Each renewal replaces the previous certificate, which is kept, so the whole history stays readable."),
        ("Un certificat prouve qu'un auditeur a reconnu votre travail",
         "Un certificat ISO 27001, par exemple : quel référentiel il couvre, quelle partie de l'organisation, qui l'a délivré et jusqu'à quand. Chaque renouvellement remplace le certificat précédent, qui est conservé : tout l'historique reste lisible."),
    ),
    "risks.assessment_list": (
        ("A risk assessment lists what could go wrong, and decides what to do about it",
         "For a scope, you name the risks, rate how likely and how serious each one is, then choose : reduce it, avoid it, share it or accept it. Run one a year, and again when something important changes."),
        ("Une appréciation des risques liste ce qui pourrait mal tourner, et décide quoi en faire",
         "Pour un périmètre, vous nommez les risques, estimez la vraisemblance et la gravité de chacun, puis choisissez : le réduire, l'éviter, le partager ou l'accepter. Menez-en une par an, et de nouveau quand quelque chose d'important change."),
    ),
    "risks.assessment_detail": (
        ("One risk assessment, from the list of risks to the decisions",
         "Its scope, the method followed, the risks found and where each one sits on the matrix. Add the risks, rate them, then move the assessment through its lifecycle : it counts in reports once validated."),
        ("Une appréciation des risques, de la liste des risques aux décisions",
         "Son périmètre, la méthode suivie, les risques relevés et la place de chacun sur la matrice. Ajoutez les risques, estimez-les, puis faites avancer l'appréciation dans son cycle de vie : elle compte dans les rapports une fois validée."),
    ),
    "risks.risk_list": (
        ("A risk is something that could go wrong, and what it would cost you",
         "The customer file leaked through a stolen laptop; production stopped by ransomware. Each risk has a likelihood and an impact, which give its level. Look first at the highest ones that have no treatment yet."),
        ("Un risque est ce qui pourrait mal tourner, et ce que cela vous coûterait",
         "Le fichier clients divulgué par le vol d'un ordinateur portable ; la production arrêtée par un rançongiciel. Chaque risque a une vraisemblance et un impact, qui donnent son niveau. Regardez d'abord les plus élevés qui n'ont pas encore de traitement."),
    ),
    "risks.risk_detail": (
        ("One risk, seen at three moments",
         "Its level with no protection at all, its level today with what is in place, and the level you aim for after treatment. Below : the assets it touches, the controls that reduce it and the decision taken. A risk above your threshold needs a treatment plan, or a formal acceptance."),
        ("Un risque, vu à trois moments",
         "Son niveau sans aucune protection, son niveau aujourd'hui avec ce qui est en place, et le niveau visé après traitement. En dessous : les biens qu'il touche, les mesures qui le réduisent et la décision prise. Un risque au-dessus de votre seuil demande un plan de traitement, ou une acceptation formelle."),
    ),
    "risks.treatment_plan_list": (
        ("A treatment plan is what you decide to do about a risk",
         "Reduce it with controls, avoid it by stopping the activity, share it through an insurance or a contract, or accept it. Each plan has an owner, dates and actions; follow it until the risk is down to the level you aimed for."),
        ("Un plan de traitement est ce que vous décidez de faire d'un risque",
         "Le réduire par des mesures, l'éviter en arrêtant l'activité, le partager par une assurance ou un contrat, ou l'accepter. Chaque plan a un propriétaire, des dates et des actions ; suivez-le jusqu'à ce que le risque soit ramené au niveau visé."),
    ),
    "risks.treatment_plan_detail": (
        ("One treatment plan, action by action",
         "The risks it treats, the option chosen, who answers for it and the actions with their dates. Update the actions as they are done, so that the plan shows where it really stands."),
        ("Un plan de traitement, action par action",
         "Les risques qu'il traite, l'option choisie, qui en répond et les actions avec leurs dates. Mettez les actions à jour au fil de leur réalisation, pour que le plan montre où il en est vraiment."),
    ),
    "risks.acceptance_list": (
        ("A risk acceptance is the formal decision to live with a risk",
         "When a risk is not worth treating further, someone entitled to decide accepts it, in writing, for a given time. An acceptance that has run out is flagged : the decision must be taken again, not assumed."),
        ("Une acceptation de risque est la décision formelle de vivre avec un risque",
         "Quand un risque ne vaut pas d'être traité davantage, une personne habilitée à décider l'accepte, par écrit, pour une durée donnée. Une acceptation arrivée à échéance est signalée : la décision doit être reprise, pas supposée."),
    ),
    "risks.acceptance_detail": (
        ("One acceptance : who decided, why, and until when",
         "The risk accepted and its level, the reason given, the person who signed and the date it runs out. Without a reason and an end date, an acceptance is only a risk someone forgot."),
        ("Une acceptation : qui a décidé, pourquoi, et jusqu'à quand",
         "Le risque accepté et son niveau, la raison donnée, la personne qui a signé et la date d'échéance. Sans raison ni date de fin, une acceptation n'est qu'un risque que quelqu'un a oublié."),
    ),
    "risks.criteria_list": (
        ("Risk criteria are the scales you rate your risks with",
         "A scale for likelihood, a scale for impact, the matrix that combines them and the level above which a risk must be treated. Agree on them once, in words everyone understands : it is what makes two assessments comparable."),
        ("Les critères de risque sont les échelles avec lesquelles vous estimez vos risques",
         "Une échelle de vraisemblance, une échelle d'impact, la matrice qui les combine et le niveau au-dessus duquel un risque doit être traité. Mettez-vous d'accord une fois, avec des mots que chacun comprend : c'est ce qui rend deux appréciations comparables."),
    ),
    "risks.criteria_detail": (
        ("One set of criteria, level by level",
         "What each level of likelihood and of impact means, the matrix they form and the threshold of acceptance. Describe each level with an example from your own business : a level nobody can picture is chosen at random."),
        ("Un jeu de critères, niveau par niveau",
         "Ce que veut dire chaque niveau de vraisemblance et d'impact, la matrice qu'ils forment et le seuil d'acceptation. Décrivez chaque niveau par un exemple tiré de votre activité : un niveau que personne ne se représente est choisi au hasard."),
    ),
    "risks.threat_list": (
        ("A threat is what could cause harm",
         "A fire, a ransomware attack, a mistake, the loss of a key person. This catalogue is the list you pick from when you describe a risk, so that the same threat bears the same name in every assessment."),
        ("Une menace est ce qui pourrait causer un dommage",
         "Un incendie, une attaque par rançongiciel, une erreur, le départ d'une personne clé. Ce catalogue est la liste dans laquelle vous piochez pour décrire un risque, afin qu'une même menace porte le même nom dans toutes les appréciations."),
    ),
    "risks.threat_detail": (
        ("One threat, and the risks it appears in",
         "What it is, whether it is deliberate or accidental, and the risks that name it. A threat that appears in many risks deserves a control of its own."),
        ("Une menace, et les risques où elle apparaît",
         "Ce qu'elle est, si elle est délibérée ou accidentelle, et les risques qui la citent. Une menace présente dans de nombreux risques mérite une mesure à elle."),
    ),
    "risks.vulnerability_list": (
        ("A vulnerability is a weakness a threat can use",
         "A server that is not updated, a shared password, a newcomer who was not trained. Record the ones you know : a risk is a threat meeting a vulnerability, and removing the weakness is often the cheapest treatment."),
        ("Une vulnérabilité est une faiblesse qu'une menace peut exploiter",
         "Un serveur qui n'est pas mis à jour, un mot de passe partagé, un nouvel arrivant qui n'a pas été formé. Consignez celles que vous connaissez : un risque est une menace qui rencontre une vulnérabilité, et supprimer la faiblesse est souvent le traitement le moins coûteux."),
    ),
    "risks.vulnerability_detail": (
        ("One vulnerability, and what it exposes",
         "How serious it is, how easy it is to use, the assets it affects and the risks it feeds. Correct it, or say why it stays : both are decisions, leaving it unrecorded is not."),
        ("Une vulnérabilité, et ce qu'elle expose",
         "Sa gravité, sa facilité d'exploitation, les biens qu'elle touche et les risques qu'elle alimente. Corrigez-la, ou dites pourquoi elle reste : les deux sont des décisions, ne pas la consigner n'en est pas une."),
    ),
    "risks.iso27005_risk_list": (
        ("An ISO 27005 analysis builds risks from your assets",
         "For each support asset, you ask which threat could use which vulnerability, and what it would do to the essential assets that rely on it. It is the detailed method of the ISO 27005 standard : slower than a simple list of risks, and harder to dispute."),
        ("Une analyse ISO 27005 construit les risques à partir de vos biens",
         "Pour chaque bien support, vous vous demandez quelle menace pourrait exploiter quelle vulnérabilité, et ce que cela ferait aux biens essentiels qui s'appuient sur lui. C'est la méthode détaillée de la norme ISO 27005 : plus lente qu'une simple liste de risques, et plus difficile à contester."),
    ),
    "risks.iso27005_risk_detail": (
        ("One scenario : an asset, a threat, a vulnerability",
         "The support asset concerned, the threat and the vulnerability that meet on it, the level that results and the treatment proposed. Check the level against your criteria before going on."),
        ("Un scénario : un bien, une menace, une vulnérabilité",
         "Le bien support concerné, la menace et la vulnérabilité qui s'y rencontrent, le niveau qui en résulte et le traitement proposé. Vérifiez le niveau au regard de vos critères avant de poursuivre."),
    ),
    "compliance.framework_list": (
        ("A framework is a set of rules you choose to comply with",
         "A standard such as ISO 27001, a law such as the GDPR, or your own internal rules. It is made of requirements, which you then check one by one. Import a framework from a file rather than typing it, and say which of your scopes it applies to."),
        ("Un référentiel est un ensemble de règles auquel vous choisissez de vous conformer",
         "Une norme comme l'ISO 27001, une loi comme le RGPD, ou vos propres règles internes. Il est fait d'exigences, que vous vérifiez ensuite une par une. Importez un référentiel depuis un fichier plutôt que de le saisir, et indiquez à quels périmètres il s'applique."),
    ),
    "compliance.framework_detail": (
        ("Everything a framework asks, section by section",
         "Its requirements in their order, the scopes it applies to and the assessments already run against it. Open a requirement to see where you stand on it. Declare a requirement not applicable only with a reason : an auditor will ask for it."),
        ("Tout ce qu'un référentiel demande, section par section",
         "Ses exigences dans leur ordre, les périmètres auxquels il s'applique et les évaluations déjà menées. Ouvrez une exigence pour voir où vous en êtes. Ne déclarez une exigence non applicable qu'avec une raison : un auditeur vous la demandera."),
    ),
    "compliance.framework_import": (
        ("Load a whole framework from a file",
         "Choose a JSON or Excel file holding the sections and the requirements. You are shown what will be created before anything is saved. Importing into a framework that already exists adds what is new and leaves the rest."),
        ("Charger un référentiel entier depuis un fichier",
         "Choisissez un fichier JSON ou Excel contenant les sections et les exigences. Vous voyez ce qui sera créé avant tout enregistrement. Importer dans un référentiel existant ajoute ce qui est nouveau et laisse le reste."),
    ),
    "compliance.requirement_list": (
        ("A requirement is one thing a framework asks of you",
         "Keeping an inventory of what you protect, or training newcomers. Each one is compliant, partly compliant, not compliant or not applicable. Filter on what is not compliant to see the work that remains."),
        ("Une exigence est une chose qu'un référentiel vous demande",
         "Tenir l'inventaire de ce que vous protégez, ou former les nouveaux arrivants. Chacune est conforme, partiellement conforme, non conforme ou non applicable. Filtrez sur ce qui n'est pas conforme pour voir le travail qui reste."),
    ),
    "compliance.requirement_detail": (
        ("Where you stand on one requirement",
         "What the framework asks, your current answer and the evidence behind it, the controls that meet it and the action plans under way. If you cannot point to evidence, the requirement is not yet compliant, whatever you believe."),
        ("Où vous en êtes sur une exigence",
         "Ce que demande le référentiel, votre réponse actuelle et la preuve qui l'appuie, les mesures qui y répondent et les plans d'action en cours. Si vous ne pouvez pas montrer de preuve, l'exigence n'est pas encore conforme, quoi que vous en pensiez."),
    ),
    "compliance.assessment_list": (
        ("A compliance assessment checks, at a given date, how far you meet a framework",
         "A self-assessment, an internal audit or a certification audit : each one goes through the requirements and records an answer for each, with the findings to correct. Run one before an audit to know where you stand."),
        ("Une évaluation de conformité vérifie, à une date donnée, où vous en êtes d'un référentiel",
         "Une auto-évaluation, un audit interne ou un audit de certification : chacune passe les exigences en revue et consigne une réponse pour chacune, avec les constats à corriger. Menez-en une avant un audit pour savoir où vous en êtes."),
    ),
    "compliance.assessment_detail": (
        ("One assessment, requirement by requirement",
         "Answer each requirement : compliant, partly, not compliant or not applicable, with the evidence you were shown. What is not met becomes a finding, and a finding an action plan. Once closed, the assessment no longer changes : it is what you showed on that day."),
        ("Une évaluation, exigence par exigence",
         "Répondez à chaque exigence : conforme, partiellement, non conforme ou non applicable, avec la preuve qui vous a été montrée. Ce qui n'est pas respecté devient un constat, et un constat un plan d'action. Une fois clôturée, l'évaluation ne change plus : elle est ce que vous avez montré ce jour-là."),
    ),
    "compliance.finding_list": (
        ("A nonconformity is a requirement or a rule that is not met",
         "It may come from an audit, from the test of a control, from an incident or from a simple observation. Record it here whatever its origin, look for its cause, and correct it through an action plan : one register answers the question of what went wrong and what was done about it (ISO 27001, clause 10.2)."),
        ("Une non-conformité est une exigence ou une règle qui n'est pas respectée",
         "Elle peut venir d'un audit, du test d'une mesure, d'un incident ou d'une simple observation. Consignez-la ici quelle que soit son origine, cherchez sa cause, et corrigez-la par un plan d'action : un seul registre répond à la question de ce qui n'allait pas et de ce qui a été fait (ISO 27001, chapitre 10.2)."),
    ),
    "compliance.action_plan_list": (
        ("An action plan is the work decided to correct a finding",
         "Who does what, by when, and how far it has got. A plan that has passed its date is flagged : a finding nobody corrects is the first thing an auditor notices."),
        ("Un plan d'action est le travail décidé pour corriger un constat",
         "Qui fait quoi, pour quand, et où il en est. Un plan qui a dépassé sa date est signalé : un constat que personne ne corrige est la première chose qu'un auditeur remarque."),
    ),
    "compliance.action_plan_detail": (
        ("One action plan, from the decision to the proof",
         "What it corrects, who answers for it, its dates and its progress. Move it through its lifecycle as the work advances, and attach what proves it was done before closing it."),
        ("Un plan d'action, de la décision à la preuve",
         "Ce qu'il corrige, qui en répond, ses dates et son avancement. Faites-le avancer dans son cycle de vie au fil du travail, et joignez ce qui prouve qu'il a été réalisé avant de le clore."),
    ),
    "compliance.mapping_list": (
        ("A mapping says that two requirements ask for the same thing",
         "ISO 27001 and NIS2 both ask you to manage incidents : map the two requirements, and the work done for one counts for the other. It is what spares you from proving the same thing twice."),
        ("Une correspondance dit que deux exigences demandent la même chose",
         "L'ISO 27001 et NIS2 demandent toutes deux de gérer les incidents : reliez les deux exigences, et le travail fait pour l'une compte pour l'autre. C'est ce qui vous évite de prouver deux fois la même chose."),
    ),
    "compliance.mapping_detail": (
        ("One link between two requirements",
         "The two requirements it joins, how close they are, and why. Say why : a mapping nobody can explain will not convince an auditor."),
        ("Un lien entre deux exigences",
         "Les deux exigences qu'il relie, leur degré de proximité, et pourquoi. Dites pourquoi : une correspondance que personne ne sait expliquer ne convaincra pas un auditeur."),
    ),
    "controls.control_list": (
        ("A control is what you actually do to reduce a risk or meet a requirement",
         "A daily backup, a rule on passwords, a training session for newcomers. Each control has an owner and tests; whether it works is read from the results of those tests, never declared. To start, create proposed controls from the requirements of a framework."),
        ("Une mesure est ce que vous faites réellement pour réduire un risque ou répondre à une exigence",
         "Une sauvegarde quotidienne, une règle sur les mots de passe, une formation des nouveaux arrivants. Chaque mesure a un propriétaire et des tests ; son efficacité se lit dans le résultat de ces tests, elle ne se déclare jamais. Pour commencer, créez des mesures proposées à partir des exigences d'un référentiel."),
    ),
    "controls.control_detail": (
        ("One control : what it does, and whether it works",
         "How it operates, the requirements it meets, the risks it treats and where it applies. Its effectiveness follows the latest validated run of each active test; when a test is overdue, the result is marked as out of date. Declaring it implemented, or retiring it, goes through its lifecycle."),
        ("Une mesure : ce qu'elle fait, et si elle fonctionne",
         "Comment elle opère, les exigences auxquelles elle répond, les risques qu'elle traite et où elle s'applique. Son efficacité suit la dernière exécution validée de chaque test actif ; quand un test est en retard, le résultat est marqué comme périmé. La déclarer mise en œuvre, ou la retirer, passe par son cycle de vie."),
    ),
    "controls.test_list": (
        ("A test checks that a control really works",
         "Restoring a backup to see that it can be read, going through the list of administrator accounts. Each test says who performs it and how often; the list shows its latest validated result and when it is next due. A test past its date is shown in red."),
        ("Un test vérifie qu'une mesure fonctionne vraiment",
         "Restaurer une sauvegarde pour voir qu'elle est lisible, relire la liste des comptes administrateurs. Chaque test dit qui le réalise et à quelle fréquence ; la liste montre son dernier résultat validé et sa prochaine échéance. Un test en retard s'affiche en rouge."),
    ),
    "controls.test_detail": (
        ("One test : what it proves, and how to run it",
         "What the test establishes, the procedure the tester follows and what a pass looks like. It can be activated once its control is planned or implemented, and it has a procedure and acceptance criteria. Record a run each time the test is performed."),
        ("Un test : ce qu'il prouve, et comment le mener",
         "Ce que le test établit, la procédure que suit le testeur et ce à quoi ressemble une réussite. Il peut être activé une fois sa mesure planifiée ou mise en œuvre, et dès qu'il a une procédure et des critères d'acceptation. Enregistrez une exécution chaque fois que le test est réalisé."),
    ),
    "controls.run_detail": (
        ("One run of a test : what was checked, and the proof",
         "Who tested, when, on which sample, with what result and which evidence. While it is in progress its content can change; once submitted it is frozen, and it is validated by someone who did not perform it. A validated run that failed, even partly, can raise a nonconformity."),
        ("Une exécution de test : ce qui a été vérifié, et la preuve",
         "Qui a testé, quand, sur quel échantillon, avec quel résultat et quelles preuves. Tant qu'elle est en cours, son contenu peut changer ; une fois soumise, elle est figée, et elle est validée par une personne qui ne l'a pas réalisée. Une exécution validée qui a échoué, même en partie, peut ouvrir une non-conformité."),
    ),
    "documents.policy_list": (
        ("A document is a written rule of the organisation",
         "The security policy, the backup procedure, the charter every user signs. Each document has at most one version in force, an owner and a review date : the owner is reminded before it falls due. Create the document, then its first version."),
        ("Un document est une règle écrite de l'organisation",
         "La politique de sécurité, la procédure de sauvegarde, la charte que signe chaque utilisateur. Chaque document a au plus une version en vigueur, un propriétaire et une date de revue : le propriétaire est prévenu avant l'échéance. Créez le document, puis sa première version."),
    ),
    "documents.policy_detail": (
        ("One document, and all its versions",
         "The version in force and who approved it, every earlier version, and the campaigns that asked people to read it. A new version starts from the one in force; once submitted its content is frozen, and putting it in force replaces the previous one. Record a review without change when the document is still right."),
        ("Un document, et toutes ses versions",
         "La version en vigueur et qui l'a approuvée, toutes les versions précédentes, et les campagnes qui ont demandé de la lire. Une nouvelle version part de celle en vigueur ; une fois soumise, son contenu est figé, et sa mise en vigueur remplace la précédente. Consignez une revue sans changement quand le document est toujours juste."),
    ),
    "documents.campaign_list": (
        ("A campaign asks people to confirm they have read a document",
         "Choose a version of a document and who must read it : users, groups or roles. Each person confirms, and each confirmation is kept as evidence. It is how you show that a rule was not only written, but made known."),
        ("Une campagne demande à des personnes de confirmer qu'elles ont lu un document",
         "Choisissez une version d'un document et qui doit la lire : des utilisateurs, des groupes ou des rôles. Chaque personne confirme, et chaque confirmation est conservée comme preuve. C'est ainsi que vous montrez qu'une règle n'a pas seulement été écrite, mais portée à la connaissance de chacun."),
    ),
    "documents.campaign_detail": (
        ("One campaign : who was asked, who confirmed",
         "Who has confirmed and when, and who has not yet. Add the people who arrived after the launch; excuse someone, with a reason, when they cannot confirm. The campaign closes by itself when its version is replaced."),
        ("Une campagne : qui a été sollicité, qui a confirmé",
         "Qui a confirmé et quand, et qui ne l'a pas encore fait. Ajoutez les personnes arrivées après le lancement ; excusez une personne, avec un motif, lorsqu'elle ne peut pas confirmer. La campagne se clôt d'elle-même quand sa version est remplacée."),
    ),
    "documents.acknowledge_list": (
        ("The documents you are asked to read",
         "Open each one, read it, and confirm. Your confirmation is recorded with its date and the sentence you accepted. The date shown is the one by which you are expected to have done it."),
        ("Les documents qu'on vous demande de lire",
         "Ouvrez chacun, lisez-le et confirmez. Votre confirmation est enregistrée avec sa date et la phrase que vous avez acceptée. La date affichée est celle avant laquelle vous êtes attendu."),
    ),
    "incidents.incident_list": (
        ("A security incident is something that harmed your information, or could have",
         "A stolen laptop, an intrusion, a message sent to the wrong person. Declare it as soon as you know : the application then follows the response step by step, and tells you who must be notified and by when."),
        ("Un incident de sécurité est ce qui a porté atteinte à vos informations, ou aurait pu",
         "Un ordinateur volé, une intrusion, un message envoyé à la mauvaise personne. Déclarez-le dès que vous le savez : l'application suit alors la réponse étape par étape, et vous dit qui doit être prévenu et dans quel délai."),
    ),
    "incidents.incident_detail": (
        ("One incident, from the first report to the lessons learned",
         "What happened and how serious it is, what was done and when, the evidence kept, and the notifications owed to authorities or to clients with their deadlines. Write things down as they happen : the chronology is what you will be asked for afterwards."),
        ("Un incident, du premier signalement aux leçons tirées",
         "Ce qui s'est passé et sa gravité, ce qui a été fait et quand, les preuves conservées, et les notifications dues aux autorités ou aux clients avec leurs délais. Notez les faits au fur et à mesure : la chronologie est ce qu'on vous demandera ensuite."),
    ),
    "incidents.event_list": (
        ("A security event is something unusual that someone reports",
         "A suspicious message, a door left open, an odd slowdown. Anyone may report one. It becomes an incident only when a named person decides so, and the events judged harmless stay here with the reason : an auditor will ask to see them."),
        ("Un événement de sécurité est un fait inhabituel que quelqu'un signale",
         "Un message suspect, une porte restée ouverte, un ralentissement étrange. Chacun peut en signaler un. Il ne devient un incident que lorsqu'une personne nommée le décide, et les événements jugés sans gravité restent ici avec la raison : un auditeur demandera à les voir."),
    ),
    "incidents.notification_list": (
        ("A notification obligation is a message you owe after an incident",
         "To the data protection authority within 72 hours, to the national incident response team, to a client under a contract. Each line says to whom, under which rule and by when; the filters show what is overdue or due within 24 hours. An obligation is created for you when an incident calls for it."),
        ("Une obligation de notification est un message que vous devez après un incident",
         "À l'autorité de protection des données sous 72 heures, au centre national de réponse aux incidents, à un client au titre d'un contrat. Chaque ligne dit à qui, selon quelle règle et pour quand ; les filtres montrent ce qui est en retard ou dû sous 24 heures. Une obligation est créée pour vous quand un incident l'exige."),
    ),
    "incidents.obligation_template_list": (
        ("An obligation template is a rule saying who must be notified, and when",
         "A personal data breach must be reported to the data protection authority within 72 hours, for example. When an incident matches a template, the obligation is created with its deadline. Changing a template changes future incidents only, never a notification already made."),
        ("Un modèle d'obligation est une règle qui dit qui doit être prévenu, et quand",
         "Une violation de données personnelles doit être déclarée à l'autorité de protection des données sous 72 heures, par exemple. Quand un incident correspond à un modèle, l'obligation est créée avec son délai. Modifier un modèle ne change que les incidents futurs, jamais une notification déjà faite."),
    ),
    "incidents.reporting_authority_list": (
        ("A reporting authority is a body you may have to notify of an incident",
         "The data protection authority, the national incident response team, the regulator of your sector. Record them once, with how to reach them : obligation templates then name them, and nobody looks for an address in the middle of a crisis."),
        ("Une autorité de notification est un organisme que vous pouvez devoir prévenir d'un incident",
         "L'autorité de protection des données, le centre national de réponse aux incidents, le régulateur de votre secteur. Enregistrez-les une fois, avec la façon de les joindre : les modèles d'obligation les citent ensuite, et personne ne cherche une adresse en pleine crise."),
    ),
    "incidents.response_plan_list": (
        ("A response plan is the procedure you follow when an incident happens",
         "Who is called, who decides, what is done first and in what order. Write it and have it approved before you need it : an incident is then handled under the plan in force, step by step."),
        ("Un plan de réponse est la procédure que vous suivez quand un incident survient",
         "Qui est appelé, qui décide, ce qui est fait en premier et dans quel ordre. Rédigez-le et faites-le approuver avant d'en avoir besoin : un incident est ensuite traité selon le plan en vigueur, étape par étape."),
    ),
    "core.lifecycle_list": (
        ("A lifecycle is the series of steps a kind of record goes through",
         "From draft to validated to archived, with the moves allowed between them and who may make each one. The lifecycles delivered with the application fit most organisations : change one only to match a real approval circuit of yours."),
        ("Un cycle de vie est la suite d'étapes par lesquelles passe un type de fiche",
         "Du brouillon à l'étape validée puis à l'archive, avec les passages permis entre elles et qui peut faire chacun. Les cycles de vie livrés avec l'application conviennent à la plupart des organisations : n'en modifiez un que pour refléter un vrai circuit d'approbation chez vous."),
    ),
}

# The rows no page shows any more.
ORPHANS = ("assets.dashboard", "compliance.dashboard", "context.dashboard", "context.site_detail", "risks.dashboard")

# (key, language) -> fingerprint of the text shipped before this migration.
SHIPPED = {
    ("accounts.access_log_list", "en"): "d6d47d2c283de2c1286c",
    ("accounts.access_log_list", "fr"): "6285c17f87261af49fff",
    ("accounts.action_log_list", "en"): "62576f6377ede8a1d5f6",
    ("accounts.action_log_list", "fr"): "388152f85138a224108a",
    ("accounts.group_detail", "en"): "e2d6818a7635196de7e1",
    ("accounts.group_detail", "fr"): "7d3f646727c1ca7cc016",
    ("accounts.group_list", "en"): "ffc4078760a1081cfb23",
    ("accounts.group_list", "fr"): "33be6ffebdcc7316c5fb",
    ("accounts.permission_list", "en"): "ea66329b5912e80087fd",
    ("accounts.permission_list", "fr"): "09f6937568bd63b35fd5",
    ("accounts.user_detail", "en"): "23354a31abec363aac79",
    ("accounts.user_detail", "fr"): "44a38906588a7f52c2c8",
    ("accounts.user_list", "en"): "81127c7c77b07712b62c",
    ("accounts.user_list", "fr"): "fa221c798e440d784ff8",
    ("assets.dashboard", "en"): "d6cbbd2672b520928a1b",
    ("assets.dashboard", "fr"): "4038a32844402a133ec4",
    ("assets.dependency_list", "en"): "376092832b50a426f876",
    ("assets.dependency_list", "fr"): "f1c65d2a6e1cc796d86d",
    ("assets.essential_asset_detail", "en"): "bf96f8f1622facaa078b",
    ("assets.essential_asset_detail", "fr"): "563398ac75fb2fe1fd60",
    ("assets.essential_asset_list", "en"): "91775e2abbe8390eb39f",
    ("assets.essential_asset_list", "fr"): "e92b8e78cb7237fedc45",
    ("assets.group_detail", "en"): "6682a5b6da61ae23334f",
    ("assets.group_detail", "fr"): "8499a7ec4dbbf9f21dd7",
    ("assets.group_list", "en"): "aa189cd37d001ef64d58",
    ("assets.group_list", "fr"): "c1016beaf43e10ed2c70",
    ("assets.site_asset_dependency_list", "en"): "cf2618bf5ef2a36c15d6",
    ("assets.site_asset_dependency_list", "fr"): "5d7f50b2a74ad78855a2",
    ("assets.site_detail", "en"): "2f9f6a46721a73b0553a",
    ("assets.site_detail", "fr"): "dad33db4e8cc54011191",
    ("assets.site_supplier_dependency_list", "en"): "e9ba1f20e69b2019295b",
    ("assets.site_supplier_dependency_list", "fr"): "9839bb1ca6a7cd870567",
    ("assets.supplier_dependency_list", "en"): "fe8809f166325e64b69c",
    ("assets.supplier_dependency_list", "fr"): "2712076b0d5a0b64a7a5",
    ("assets.supplier_detail", "en"): "228595d0c624477c74ab",
    ("assets.supplier_detail", "fr"): "28b839f938ca2204001a",
    ("assets.supplier_list", "en"): "5e1d24ac532a4a6beb50",
    ("assets.supplier_list", "fr"): "991e80e50ba3218c7259",
    ("assets.supplier_requirement_detail", "en"): "b8d0031eccf379745826",
    ("assets.supplier_requirement_detail", "fr"): "432b043391cba9103f1d",
    ("assets.supplier_type_detail", "en"): "1d8b2430a35c09edc84f",
    ("assets.supplier_type_detail", "fr"): "7eb7378f2ccb8d28c424",
    ("assets.supplier_type_list", "en"): "4b5e4b9321d869d3cd1f",
    ("assets.supplier_type_list", "fr"): "eab4c72dcb23e4950eea",
    ("assets.support_asset_detail", "en"): "117a53f1955725db8982",
    ("assets.support_asset_detail", "fr"): "cc16b8738b91c74aa0b7",
    ("assets.support_asset_list", "en"): "f6f9dc2bad7aa6715f8f",
    ("assets.support_asset_list", "fr"): "cd0404da628e5f8be1a1",
    ("compliance.action_plan_detail", "en"): "396218fb16cebecbf5bf",
    ("compliance.action_plan_detail", "fr"): "70187d609d0aedc28585",
    ("compliance.action_plan_list", "en"): "3e4cfc649500d7501772",
    ("compliance.action_plan_list", "fr"): "38e3ad99b677b72fef66",
    ("compliance.assessment_detail", "en"): "a72019a2179be54e8915",
    ("compliance.assessment_detail", "fr"): "0e14afa9c162400e7f02",
    ("compliance.assessment_list", "en"): "1aacd5dc80123de87cdb",
    ("compliance.assessment_list", "fr"): "a668818e83425d97d14c",
    ("compliance.dashboard", "en"): "a92419b30c03a3880d2a",
    ("compliance.dashboard", "fr"): "351d8b3418f9db732f7c",
    ("compliance.framework_detail", "en"): "fb21c83ac50aa437a63a",
    ("compliance.framework_detail", "fr"): "29194afb42ffc59002d6",
    ("compliance.framework_import", "en"): "4a785721a30f402d2c17",
    ("compliance.framework_import", "fr"): "74422352acb7701cc812",
    ("compliance.framework_list", "en"): "f29b1eecc99761b150ff",
    ("compliance.framework_list", "fr"): "3ad086aae6c1880b7bb2",
    ("compliance.mapping_detail", "en"): "7ce4a83109029fa4b537",
    ("compliance.mapping_detail", "fr"): "071fd46b1fa71701a9e1",
    ("compliance.mapping_list", "en"): "a467111390d9d85f91a0",
    ("compliance.mapping_list", "fr"): "ed776061c0c32235c492",
    ("compliance.requirement_detail", "en"): "bfac3fe6718c97efaabc",
    ("compliance.requirement_detail", "fr"): "b4624cfe12c58543f97d",
    ("compliance.requirement_list", "en"): "81838a4dc8ef8a6a58da",
    ("compliance.requirement_list", "fr"): "56d191eb1bd91ea9e642",
    ("context.activity_detail", "en"): "964a0b8bbc15571c4389",
    ("context.activity_detail", "fr"): "0becaea68c5bd52d234e",
    ("context.activity_list", "en"): "0d0d40ae0e3c94cb8791",
    ("context.activity_list", "fr"): "d2740818b4cbf7422565",
    ("context.dashboard", "en"): "21b1789b46097aa45fdd",
    ("context.dashboard", "fr"): "24188f19ae32d343cd69",
    ("context.indicator_detail", "en"): "cf8f57e580f03887ac80",
    ("context.indicator_detail", "fr"): "942b98c24a1d6589f98b",
    ("context.indicator_list", "en"): "ad8b77ca5ed4d01addaa",
    ("context.indicator_list", "fr"): "0498448d20d6fb9e23d1",
    ("context.issue_detail", "en"): "575ce588c4aeeef7a85f",
    ("context.issue_detail", "fr"): "613d026f34d3d65278fc",
    ("context.issue_list", "en"): "21e1d4828321c9992cf9",
    ("context.issue_list", "fr"): "5f665bf54cb954418e0f",
    ("context.objective_detail", "en"): "30d67a833ab6759e5970",
    ("context.objective_detail", "fr"): "9de26243f1499fbdcbdc",
    ("context.objective_list", "en"): "7291e00611d25210891e",
    ("context.objective_list", "fr"): "75af5b4a7bb13b062d20",
    ("context.role_detail", "en"): "9b37ae9d26d52f7e7189",
    ("context.role_detail", "fr"): "bfa79fbff9da7f7f43c6",
    ("context.role_list", "en"): "251866f4eb74e8d03e47",
    ("context.role_list", "fr"): "78599cc21bda27145a91",
    ("context.scope_detail", "en"): "1af60d235905813d4bdf",
    ("context.scope_detail", "fr"): "4dcfd293e54262880568",
    ("context.scope_list", "en"): "0a2ba3398b09f6075e37",
    ("context.scope_list", "fr"): "de82ab237685eb133620",
    ("context.site_detail", "en"): "ecca7910064d799a082d",
    ("context.site_detail", "fr"): "6111a4a9a2480b3ae91f",
    ("context.site_list", "en"): "0f5019e373160bce4c95",
    ("context.site_list", "fr"): "b8053d677146ab1c56ad",
    ("context.stakeholder_detail", "en"): "bdb7ab8d5c3dcc71c258",
    ("context.stakeholder_detail", "fr"): "016759abb57b4e8663be",
    ("context.stakeholder_list", "en"): "87c24df3f6a168f15fe3",
    ("context.stakeholder_list", "fr"): "bbfcb50352e8cbc9f1f4",
    ("context.swot_detail", "en"): "266169421452aa16c427",
    ("context.swot_detail", "fr"): "8c1bbb3441702500f629",
    ("context.swot_list", "en"): "1e254ed92931c7290e26",
    ("context.swot_list", "fr"): "61fd27203bb1376ef2e3",
    ("context.tag_list", "en"): "585ad8dfe9ab2465bf88",
    ("context.tag_list", "fr"): "c0b446598f1f049ee555",
    ("controls.control_detail", "en"): "4a3c3d89281baf8f5446",
    ("controls.control_detail", "fr"): "9c29c93b26ed902cb889",
    ("controls.control_list", "en"): "551dc415e94ea73bec86",
    ("controls.control_list", "fr"): "36da88b1ec06f4699d18",
    ("controls.run_detail", "en"): "ba67ee2a3d82c3f7a588",
    ("controls.run_detail", "fr"): "91786697db69919ce98c",
    ("controls.test_detail", "en"): "96f1204a7e3c9d4d04eb",
    ("controls.test_detail", "fr"): "bd830bbe1477b5962877",
    ("controls.test_list", "en"): "52ec5bca2fd11af71ce3",
    ("controls.test_list", "fr"): "38f0ee022bdcbae35f35",
    ("documents.acknowledge_list", "en"): "b08862375fdcfa81e1ed",
    ("documents.acknowledge_list", "fr"): "c1c5ce2730663b567e30",
    ("documents.campaign_detail", "en"): "dfda8d787ccecb47e03b",
    ("documents.campaign_detail", "fr"): "893032113145df128710",
    ("documents.campaign_list", "en"): "7cada40d5a3440482469",
    ("documents.campaign_list", "fr"): "02816f0e5ce18a717f6b",
    ("documents.policy_detail", "en"): "8636192b81f41d58089a",
    ("documents.policy_detail", "fr"): "09ceb651ed518bd73436",
    ("documents.policy_list", "en"): "5a1371508c1cf0f176e8",
    ("documents.policy_list", "fr"): "8e7dc64de9785999f90f",
    ("home", "en"): "368c00887e647d93d330",
    ("home", "fr"): "99baa6136460e79ecd6f",
    ("risks.acceptance_detail", "en"): "993281598928051632fb",
    ("risks.acceptance_detail", "fr"): "f4861fc98b1451def70d",
    ("risks.acceptance_list", "en"): "68f0a97d568e3f6007a4",
    ("risks.acceptance_list", "fr"): "6ff6fc8c192d5846e959",
    ("risks.assessment_detail", "en"): "24625ce1ce9d1b7a7d28",
    ("risks.assessment_detail", "fr"): "d666c63f0cf83dd8ed0f",
    ("risks.assessment_list", "en"): "7ace59c1529a75360de8",
    ("risks.assessment_list", "fr"): "a121b50c626395c38e2a",
    ("risks.criteria_detail", "en"): "c47e470e2e0b945263b8",
    ("risks.criteria_detail", "fr"): "a13ab68ed8619d89f1e6",
    ("risks.criteria_list", "en"): "81f00d29ec94090bb97d",
    ("risks.criteria_list", "fr"): "7e9b888316e0d309c84e",
    ("risks.dashboard", "en"): "d91ee7a29b133ea88485",
    ("risks.dashboard", "fr"): "d917d4549371d03472ec",
    ("risks.iso27005_risk_detail", "en"): "f4eac5a7ca092eb348f1",
    ("risks.iso27005_risk_detail", "fr"): "39d85ff0efeee450dfae",
    ("risks.iso27005_risk_list", "en"): "b476153ee23b8b8d3359",
    ("risks.iso27005_risk_list", "fr"): "b852b3e6bda06fc8d6af",
    ("risks.risk_detail", "en"): "d9cac568e4ecf8ceb0f9",
    ("risks.risk_detail", "fr"): "fa0a13aa58f9ee3073bc",
    ("risks.risk_list", "en"): "1543b6bf72e334f33a07",
    ("risks.risk_list", "fr"): "379e14910389e24dbc34",
    ("risks.threat_detail", "en"): "8a0126385f70c06a7eb7",
    ("risks.threat_detail", "fr"): "0eff2704f2ef45dc4290",
    ("risks.threat_list", "en"): "4222ad492b18dc6bf2f0",
    ("risks.threat_list", "fr"): "5b6699788fa3f4ce3146",
    ("risks.treatment_plan_detail", "en"): "4008f131fc549d0092ea",
    ("risks.treatment_plan_detail", "fr"): "be33c5b49b019d29623f",
    ("risks.treatment_plan_list", "en"): "4780338cdcf126cb0076",
    ("risks.treatment_plan_list", "fr"): "e96b93b4ba2d6f1e1f03",
    ("risks.vulnerability_detail", "en"): "41832d4812ea49a75ef2",
    ("risks.vulnerability_detail", "fr"): "afa94b2cf40efbbff067",
    ("risks.vulnerability_list", "en"): "eaefb2d8bfaf2cc78271",
    ("risks.vulnerability_list", "fr"): "865f02912228470f1be5",
}


def fingerprint(title, body):
    """What recognises a text without keeping it."""
    return hashlib.sha256(f"{title}\n{body}".encode()).hexdigest()[:20]


def _untouched(row):
    """Whether ``row`` still holds the text a previous migration shipped."""
    return SHIPPED.get((row.key, row.language)) == fingerprint(row.title, row.body)


def plain_words(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    for key, texts in HELP.items():
        for language, (title, body) in zip(("en", "fr"), texts):
            row = HelpContent.objects.filter(key=key, language=language).first()
            if row is None:
                HelpContent.objects.create(key=key, language=language, title=title, body=body)
            elif _untouched(row):
                row.title, row.body = title, body
                row.save()
    for row in HelpContent.objects.filter(key__in=ORPHANS):
        if _untouched(row):
            row.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0011_plain_words_scope_and_asset_help"),
    ]

    operations = [
        migrations.RunPython(plain_words, migrations.RunPython.noop),
    ]
