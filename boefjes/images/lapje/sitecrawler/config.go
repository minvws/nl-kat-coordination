package main

import (
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

func (c *Config) ReadUrls(url string) (e error) {
	c.Urls = append(c.Urls, Url{Id: 0, Url: url})

	c.Logger.Println("Crawling", url)
	return nil
}
