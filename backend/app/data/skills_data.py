"""Curated skill catalog (VERIFIED knowledge, as opposed to anything model-generated).

SKILLS rows: (slug, name, category, difficulty 1-5, aliases, prerequisites, description)
"""

SKILLS = [
 ("python","Python","Programming",2,["python3","py","python programming"],[],"General-purpose language used for scripting, data work, ML and backends."),
 ("sql","SQL","Data",2,["structured query language","mysql","postgresql","postgres","sqlite","t-sql","pl/sql"],[],"Language for querying and modelling relational data."),
 ("git","Git","Tools",1,["github","gitlab","version control","bitbucket"],[],"Distributed version control for tracking and collaborating on code."),
 ("linux","Linux","Tools",2,["bash","shell scripting","unix","shell"],[],"Command line and operating-system fundamentals used across engineering roles."),
 ("javascript","JavaScript","Programming",2,["js","es6","ecmascript","vanilla js"],[],"The language of the browser; also used server-side."),
 ("typescript","TypeScript","Programming",2,["ts"],["javascript"],"Typed superset of JavaScript."),
 ("html","HTML","Web",1,["html5"],[],"Markup language for web page structure."),
 ("css","CSS","Web",1,["css3","tailwind","tailwind css","sass","scss"],[],"Styling and layout for the web."),
 ("react","React","Web",3,["reactjs","react.js","react js"],["javascript","html","css"],"Component-based UI library."),
 ("nodejs","Node.js","Web",3,["node","node js","expressjs","express.js"],["javascript"],"JavaScript runtime for backend services."),
 ("rest-apis","REST APIs","Web",2,["restful","api development","web apis","restful apis"],[],"Designing and consuming HTTP APIs."),
 ("mongodb","MongoDB","Data",2,["mongo","nosql"],[],"Document-oriented NoSQL database."),
 ("java","Java","Programming",3,["core java","java8","java 8","java 17"],[],"Statically typed, object-oriented language widely used in enterprise."),
 ("cpp","C++","Programming",3,["cpp","c plus plus"],[],"Systems and performance-oriented language."),
 ("data-structures-algorithms","Data Structures & Algorithms","Programming",3,["dsa","algorithms","data structures","data structures and algorithms"],[],"Core problem-solving toolkit for software engineering."),
 ("software-testing","Software Testing","Engineering",2,["unit testing","pytest","jest","tdd","test driven development"],[],"Writing automated tests and reasoning about quality."),
 ("system-design","System Design","Engineering",4,["distributed systems","scalability"],["rest-apis","sql"],"Designing scalable, reliable systems."),
 ("statistics","Statistics","Mathematics",3,["stats","descriptive statistics","hypothesis testing","statistical analysis"],[],"Describing data and drawing inferences under uncertainty."),
 ("probability","Probability","Mathematics",3,["bayes","bayesian"],[],"Reasoning about random events and distributions."),
 ("linear-algebra","Linear Algebra","Mathematics",3,["matrix algebra"],[],"Vectors, matrices and transformations underpinning ML."),
 ("numpy","NumPy","Data Processing",2,["np"],["python"],"Numerical arrays and vectorised computation in Python."),
 ("pandas","Pandas","Data Processing",2,["pd","dataframes","dataframe"],["python","numpy"],"Tabular data manipulation in Python."),
 ("data-visualization","Data Visualization","Data",2,["matplotlib","seaborn","plotly","data viz","dataviz"],["python"],"Communicating data with charts."),
 ("excel","Excel","Tools",1,["microsoft excel","ms excel","spreadsheets","advanced excel"],[],"Spreadsheet analysis, formulas and pivots."),
 ("bi-tools","BI Tools","Data",2,["tableau","power bi","powerbi","looker","business intelligence"],[],"Dashboarding tools such as Tableau and Power BI."),
 ("machine-learning","Machine Learning","Machine Learning",3,["ml","machine learning fundamentals","supervised learning","unsupervised learning"],["statistics","numpy","pandas"],"Learning predictive models from data."),
 ("feature-engineering","Feature Engineering","Machine Learning",3,["feature selection","feature extraction"],["pandas","machine-learning"],"Turning raw data into model inputs."),
 ("model-evaluation","Model Evaluation","Machine Learning",3,["cross validation","cross-validation","evaluation metrics","model validation"],["machine-learning"],"Measuring whether a model will generalise."),
 ("scikit-learn","Scikit-learn","Frameworks",3,["sklearn","scikit learn"],["machine-learning"],"Classical ML library for Python."),
 ("neural-networks","Neural Networks","Deep Learning",3,["mlp","neural nets","multilayer perceptron"],["machine-learning","linear-algebra"],"Layered, differentiable function approximators."),
 ("deep-learning","Deep Learning","Deep Learning",4,["dl","deep neural networks"],["neural-networks"],"Training deep architectures at scale."),
 ("cnn","CNN","Deep Learning",4,["convolutional neural networks","convnet","convolutional neural network"],["deep-learning"],"Convolutional networks for images."),
 ("rnn","RNN","Deep Learning",4,["lstm","gru","recurrent neural networks","recurrent neural network"],["deep-learning"],"Recurrent networks for sequences."),
 ("transformers","Transformers","Deep Learning",5,["bert","gpt","hugging face transformers","huggingface","hugging face"],["deep-learning"],"Attention-based architectures behind modern NLP and LLMs."),
 ("pytorch","PyTorch","Frameworks",4,["torch"],["python","deep-learning"],"Deep learning framework."),
 ("tensorflow","TensorFlow","Frameworks",4,["tf","keras"],["python","deep-learning"],"Deep learning framework."),
 ("nlp","NLP","Machine Learning",4,["natural language processing","text mining","spacy","nltk","text classification"],["machine-learning"],"Machine learning on text."),
 ("computer-vision","Computer Vision","Machine Learning",4,["cv","opencv","image processing","image classification","object detection"],["cnn"],"Machine learning on images and video."),
 ("generative-ai","Generative AI","Machine Learning",4,["genai","llm","llms","large language models","prompt engineering","rag","retrieval augmented generation","langchain"],["transformers"],"Building with large generative models."),
 ("fastapi","FastAPI","Frameworks",2,["fast api"],["python","rest-apis"],"Modern Python web framework for APIs."),
 ("docker","Docker","Deployment",3,["containers","containerization","dockerfile","docker compose","docker-compose"],["linux"],"Packaging software into containers."),
 ("kubernetes","Kubernetes","Deployment",4,["k8s"],["docker"],"Container orchestration."),
 ("aws","AWS","Cloud",3,["amazon web services","ec2","s3","lambda","sagemaker","amazon aws"],["linux"],"Amazon's cloud platform."),
 ("azure","Azure","Cloud",3,["microsoft azure"],["linux"],"Microsoft's cloud platform."),
 ("gcp","GCP","Cloud",3,["google cloud","google cloud platform"],["linux"],"Google's cloud platform."),
 ("ci-cd","CI/CD","Deployment",3,["cicd","github actions","jenkins","gitlab ci","continuous integration","continuous delivery"],["git"],"Automated build, test and release pipelines."),
 ("terraform","Terraform","Deployment",4,["infrastructure as code","iac"],["linux"],"Declarative infrastructure provisioning."),
 ("networking","Networking","Infrastructure",2,["tcp/ip","dns","http","network fundamentals","tcp ip"],[],"How machines talk: IP, DNS, HTTP, TLS."),
 ("security-fundamentals","Security Fundamentals","Security",2,["cybersecurity","infosec","owasp","encryption","cryptography","pen testing","penetration testing","information security"],["networking"],"Threats, controls and secure design basics."),
 ("figma","Figma","Design",1,["figma design","sketch","adobe xd"],[],"Interface design and prototyping tool."),
 ("ux-research","UX Research","Design",2,["user research","usability testing"],[],"Understanding users through research."),
 ("wireframing","Wireframing & Prototyping","Design",2,["wireframes","prototyping","wireframe"],[],"Low- and high-fidelity interface sketches."),
 ("design-systems","Design Systems","Design",3,["design system","ui design"],["figma"],"Reusable components and design tokens."),
]

SOFT_SKILLS = ["communication","teamwork","leadership","problem solving","time management","collaboration","mentoring","presentation","stakeholder management","adaptability","critical thinking"]

# Official documentation roots that are stable. Anything not listed gets no docs link (never invented).
DOCS_URLS = {
 "python":"https://docs.python.org/3/tutorial/","numpy":"https://numpy.org/doc/stable/user/","pandas":"https://pandas.pydata.org/docs/user_guide/",
 "scikit-learn":"https://scikit-learn.org/stable/user_guide.html","pytorch":"https://pytorch.org/tutorials/","tensorflow":"https://www.tensorflow.org/tutorials",
 "docker":"https://docs.docker.com/get-started/","kubernetes":"https://kubernetes.io/docs/tutorials/","fastapi":"https://fastapi.tiangolo.com/tutorial/",
 "react":"https://react.dev/learn","typescript":"https://www.typescriptlang.org/docs/","javascript":"https://developer.mozilla.org/en-US/docs/Web/JavaScript",
 "html":"https://developer.mozilla.org/en-US/docs/Learn/HTML","css":"https://developer.mozilla.org/en-US/docs/Learn/CSS","git":"https://git-scm.com/doc",
 "nodejs":"https://nodejs.org/en/learn","mongodb":"https://www.mongodb.com/docs/manual/","aws":"https://docs.aws.amazon.com/","terraform":"https://developer.hashicorp.com/terraform/docs",
"sql":"https://www.postgresql.org/docs/current/tutorial.html","linux":"https://man7.org/linux/man-pages/",
 "azure":"https://learn.microsoft.com/azure/","gcp":"https://cloud.google.com/docs","transformers":"https://huggingface.co/docs/transformers/","ci-cd":"https://docs.github.com/actions",
 "software-testing":"https://docs.pytest.org/","data-visualization":"https://matplotlib.org/stable/tutorials/","nlp":"https://spacy.io/usage",
}

# Taxonomy trees. Leaves double as the self-assessment checklist for a skill.
TAXONOMY = {
 "python": {"Fundamentals":["Syntax","Variables","Data Types","Operators"],"Control Flow":["Conditions","Loops"],"Functions":[],"Data Structures":["Lists","Dictionaries","Sets","Tuples"],"OOP":["Classes","Inheritance"],"File Handling":[],"Exceptions":[],"Modules":["Packages","Virtual environments"],"Advanced Python":["Generators","Decorators","Async"],"Ecosystem":["NumPy","Pandas","FastAPI","Django","PyTorch"]},
 "sql": {"Querying":["SELECT","WHERE","ORDER BY","LIMIT"],"Aggregation":["GROUP BY","HAVING","Aggregate functions"],"Joins":["INNER JOIN","LEFT JOIN","Self joins"],"Subqueries & CTEs":[],"Window Functions":["ROW_NUMBER","RANK","LAG/LEAD"],"Data Modelling":["Normalisation","Keys & constraints"],"Performance":["Indexes","Query plans"]},
 "statistics": {"Descriptive":["Mean/median/mode","Variance & std deviation","Distributions"],"Inference":["Sampling","Confidence intervals","Hypothesis tests","p-values"],"Relationships":["Correlation","Linear regression"]},
 "machine-learning": {"Supervised":["Regression","Classification"],"Unsupervised":["Clustering","Dimensionality reduction"],"Data Preparation":["Train/test split","Feature scaling","Handling missing data"],"Model Quality":["Overfitting","Regularisation","Cross-validation","Metrics"]},
 "deep-learning": {"Foundations":["Neurons & layers","Activation functions","Backpropagation","Optimisers"],"Architectures":["CNN","RNN/LSTM","Transformers"],"Practice":["Regularisation (dropout)","Batch normalisation","Transfer learning","GPU training"]},
 "javascript": {"Core":["Variables & scoping","Functions & closures","Objects & prototypes","Arrays & iteration"],"Async":["Promises","async/await","Event loop"],"Browser":["DOM","Events","Fetch API"],"Modern JS":["Modules","Destructuring"]},
 "react": {"JavaScript":[],"HTML":[],"CSS":[],"React Fundamentals":["JSX","Components","Props","State"],"Hooks":["useState","useEffect","Custom hooks"],"Routing":[],"State Management":[],"API Integration":[],"Testing":[],"Next.js":[]},
 "docker": {"Core":["Images","Containers","Dockerfile","Volumes","Networking"],"Compose":["Multi-container apps"],"Practice":["Image size & layers","Registries","Security basics"]},
 "git": {"Basics":["add/commit","branches","merge","remotes"],"Collaboration":["Pull requests","Rebasing","Resolving conflicts"]},
 "aws": {"Compute":["EC2","Lambda"],"Storage":["S3","EBS"],"Networking":["VPC","Route 53"],"Security":["IAM"],"Data & ML":["RDS","SageMaker"]},
 "numpy": {"Arrays":["Creation","Indexing & slicing","Reshaping"],"Operations":["Broadcasting","Vectorisation","Linear algebra routines"]},
 "pandas": {"Structures":["Series","DataFrame"],"Wrangling":["Selection","Filtering","Grouping","Merging/joining","Handling missing data"],"I/O":["CSV","SQL"]},
}

def taxonomy_leaves(slug):
    """Flat checklist for a skill: leaf names, or the group name when a group has no leaves."""
    tree = TAXONOMY.get(slug)
    if not tree:
        return []
    out = []
    for group, kids in tree.items():
        out.extend(kids if kids else [group])
    return out
