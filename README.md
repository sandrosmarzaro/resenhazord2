<h1 align="center"><b>🗿 Resenhazord 2️⃣</b></h1>

## 📑 Index

1. <a href="#resume">Resume</a>
2. <a href="#run">How To Run</a>
3. <a href="#contribute">How To Contribute</a>

## 📜 Resume <a id="resume"></a>

Resenhazord 2 it's a funny Whatsapp chatbot make by [A Resenha](https://github.com/a-resenha) to Resenha. Your first discontinued version, the [Resenhazord](https://github.com/sandrosmarzaro/resenhazord-chatbot), was made by the [Venom](https://github.com/orkestral/venom) library, it was a side project at the beginning of the undergraduate program, which caused several defects. Due to this, this version was created, which seeks better readability and organization of the project, now using the [Baileys](https://github.com/WhiskeySockets/Baileys) library. Feel free to download, test, use, and contribute.

## 💻 How To Run <a id="run"></a>

### 🐧 Ubuntu Requirements

#### 1º Installing NVM, NodeJS and NPM
First you need to [JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript) runtime, in this case, using [NodeJS](https://nodejs.org/en), in terminal run:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```
To download Node Version Manager (NVM), and to install Node:
```bash
nvm install 20
```
You can verify if the installation was correct with:
```bash
node -v
```
To see the NodeJS version installed, and the version of Node Package Manager ([NPM](https://www.npmjs.com/))
```bash
npm -v
```
#### 2º Insalling Yarn
But instead of using NPM to conrol the packages, we using [Yarn](https://yarnpkg.com/) globally, running this code:
```bash
npm install --global yarn
```
Verifing the installation:
```bash
yarn -v
```

#### 3º Installing Git, Clone App, Install and Run

Now you can clone the repository using [Git](https://git-scm.com/):
```bash
sudo add-apt-repository ppa:git-core/ppa
```
To add the PPA, and to really install Git:
```bash
sudo apt update; apt install git
```
Finally you can download project with:
```bash
git clone git@github.com:a-resenha/resenhazord2.git
```
Enter the directory of the bot:
```bash
cd resenhazord2/
```
Execute this command to install all dependencies of bot:
```bash
yarn install
```
Towards the end, run the Resenhazord 2 running:
```bash
yarn start
```

## 🏗️ How To Contribute <a id="contribute"></a>
#### 1º Create a Git Branch
First you need have the resenhazord2 repository downloaded, like was make in third pass of Ubuntu requirements section. With this, you must create a Git branch follows the [conventional commits pattern](https://medium.com/linkapi-solutions/conventional-commits-pattern-3778d1a1e657) in the name of branch.

```bash
git branch type/name-of-the-branch
```

The type are one of the following: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `revert`.
<!-- faça uma tabela centralizada com cabeçalhos de tipo e descrição para cada tipo da convenção-->

| Type | Description |
|:----:|:-----------:|
| feat | A new feature |
| fix | A bug fix |
| docs | Documentation only changes |
| style | Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc) |
| refactor | A code change that neither fixes a bug nor adds a feature |
| perf | A code change that improves performance |
| test | Adding missing tests or correcting existing tests |
| chore | Changes to the build process or auxiliary tools and libraries such as documentation generation |
| revert | Revert to a commit |

And enter in this branch created running:

```bash
git checkout type/name-of-the-branch
```

#### 2º Commit Changes
After you made your changes to the created branch, you must add to the commit and then again following the naming pattern mentioned:

```bash
git add path/to/file.extention
```
Is import that you make [atomic commits](https://community.revelo.com.br/commits-atomicos-o-que-sao/), that is, a commit for each modification made, using the command:

```bash
git commit -m "type: describe your modifications"
```

#### 3º Push Branch
After you have made your commits, you must push the branch to the repository:

```bash
git push origin type/name-of-the-branch
```

#### 4º Create Pull Request
After you have pushed the branch to the repository, you must create a pull request to the main branch, explaining what you did in your modifications.
Follow the link created in the terminal or go to the repository on GitHub and click on the "Pull Request" button.

#### 5º Wait for Review
After creating the pull request, wait for the review of the project maintainers, who will analyze your modifications and approve or request changes.

