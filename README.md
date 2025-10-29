# Introduction

This project allows you to **freely** retrieve questions and answers from a dump on the https://examtopics.com website 💸.\
While the site normally offers paid access, it’s possible to access the discussion editor interface for free through a direct URL. In this interface, you can view all the questions, answers, and comments. This mechanism is the foundation of the automation implemented in this project. You can either browse the discussion pages manually or use my automated solution.

# How works the discussion URLs (questions + answers + comments) ?

You can access to the discussion interface with this URL : https://www.examtopics.com/discussions/fortinet/ or https://www.examtopics.com/discussions/google/ (change fortinet or google by the name of provider that you want). With these URLs you can list all the discussions of a provider.

Each discussion has an URL like this : 
https://www.examtopics.com/discussions/fortinet/view/308507-exam-fcp_fgt_ad-76-topic-1-question-13-discussion/
OR
https://www.examtopics.com/discussions/fortinet/view/311541-exam-fcp_fgt_ad-76-topic-1-question-25-discussion/

As you can see, in each URL, there is :
* An id
* The exam name
* The question number

But in reality, only the id is important.\
For exemple if you try to go to : https://www.examtopics.com/discussions/fortinet/view/308507-exam-fcp_fgt_ad-76-topic-1-question-25-discussion/ (An URL with an ID that does not correspond to the question)
You will be redirect to https://www.examtopics.com/discussions/fortinet/view/308507-exam-fcp_fgt_ad-76-topic-1-question-13-discussion/ (the good URL)

So the most important is to get all the id, but they are not all in sequence; they are mixed in with questions from other exams. **It's why we will use the point 2 to get a list of all the id (or almost 😅).**

Another subtle point is that on the discussion page, you only see discussions that have at least one comment. So with point 2, you may not be able to retrieve all the id, **we will use the point 3 for this**. If you have been looking for a referenced exam for a while, there should be at least one comment on all questions, so you do not need to do point 3. You can still look at the urls.txt file to see if all the questions that the dump has are there.

# 1. Clone this project

First, clone this project : 

``` bash
git clone https://github.com/Victor-G8/free-examtopics-dumps.git
```

And install Docker on your machine if it is not already done (there is a lot of tutorials on internet).

# 2. Get lists of discussion URLs

For this point, we will use this great project  : https://github.com/thatonecodes/examtopics-downloader

Run a Docker container like this :

```bash
docker run -it \
  --name examtopics-url-builder-ctn \
  ghcr.io/thatonecodes/examtopics-downloader:latest \
  -p fortinet -s fcp_fgt_ad-76 \
  -save-links -no-cache
docker cp examtopics-url-builder-ctn:/app/saved-links.txt ./urls.txt
docker rm examtopics-url-builder-ctn
docker image rm ghcr.io/thatonecodes/examtopics-downloader
```

Here fortinet is the name of the provider and fcp_fgt_ad-76 the name of the exam. The -no-cache is important because this project don't have a complete cache up to date with all the dumps, it's better to retrieve information directly from examtopics.

Be careful with the name of the exam because sometimes it's not exactly like the exam URL.\
For exemple here, the url of the exam is : https://www.examtopics.com/exams/fortinet/fcp-fgt-ad-7-6/  
But the name of the exam in the discussions is fcp_fgt_ad-76 (and not fcp-fgt-ad-7-6).

With this script, you will get a list of the discussions URLs for your exam. If you have all the URLs in the urls.txt file, pass to the point 4, else pass to the point 3.

# 3. Complete list of discussion URLs

If you want to know an estimate range to test (the lower to the higher id) :
```bash
docker build -t scrap-img .
docker run --rm -v ${PWD}/urls.txt:/app/urls.txt scrap-img python complete-list.py estimate
```
You can use the range in the next command. If there is too much you can split or search only the range that seems right to you

For the next part, i advise you to use a VPN because we will send a lot of requests to the examtopics website.

To run the script to detect the missing discussions + add them in the urls.txt list :
```bash
docker build -t scrap-img .
docker run --rm -it -v ${PWD}/urls.txt:/app/urls.txt scrap-img python complete-list.py search <Number of questions> <Start of range> <End of range>
```
For exemple `python complete-list.py search 84 306000 308000` means 84 questions and the range of id 306000-308000 (2000 id will be test with this command)

# 4. Create a full PDF with all the questions, answers and comments

Here is the command to run the script scraper-and-pdf-generator.py and generate the pdf file `dump.pdf`

``` bash
docker build -t scrap-img .
docker run -it --name scraper-and-pdf-generator-ctn -v ${PWD}/urls.txt:/app/urls.txt scrap-img python scraper-and-pdf-generator.py
docker cp scraper-and-pdf-generator-ctn:/app/dump.pdf .
docker cp scraper-and-pdf-generator-ctn:/app/complete-list-output . # Optionnal
docker rm scraper-and-pdf-generator-ctn
docker image rm scrap-img
```

**You have now a full PDF to revise for your exam for free, don't forget to add a star on this project if it helped you 😉**
