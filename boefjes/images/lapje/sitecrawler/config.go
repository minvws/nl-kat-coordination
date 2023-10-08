package main

import (
	"bufio"
	"log"
	"os"
	"path"
)

type Url struct {
	Id  uint
	Url string
}

type Config struct {
	OutputDir      string
	ProfileDir     string
	ScreenshotDir  string
	Port           uint
	Urls           []Url
	RepeatCrawl    uint
	ShuffleUrls    bool
	TakeScreenshot bool
	NumTabs        uint
	Logger         *log.Logger
}

func (c *Config) OpenLogger(filename string) (e error) {
	logfile, err := os.Create(filename)
	if err != nil {
		return err
	}
	//defer logfile.Close()

	c.Logger = log.New(logfile, "sitecrawler: ", log.Ldate|log.Ltime|log.Lshortfile)
	return nil
}

func (c *Config) OpenDefaultLogger() (e error) {
	return c.OpenLogger(path.Join(c.OutputDir, "log.txt"))
}

func (c *Config) ReadUrls(filename string) (e error) {

	readFile, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer readFile.Close()
	fileScanner := bufio.NewScanner(readFile)
	fileScanner.Split(bufio.ScanLines)
	id := uint(1)
	for fileScanner.Scan() {
		c.Urls = append(c.Urls, Url{Id: id, Url: fileScanner.Text()})
		id += 1
	}
	c.Logger.Println("Read", id-1, "urls from", filename)
	return nil
}
