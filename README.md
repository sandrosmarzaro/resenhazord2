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
Transpile the TypeScript files with:
```bash
yarn build
```
Towards the end, run the Resenhazord 2 running:
```bash
yarn start
```
Or the to development cases:
```bash
yarn dev
```

## 🏗️ How To Contribute <a id="contribute"></a>