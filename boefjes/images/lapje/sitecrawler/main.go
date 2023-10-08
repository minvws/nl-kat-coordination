package main

import (
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path"
	"time"
)

func main() {
	proxyPort := flag.Uint("p", 8080, "Port that mitmproxy will listen on.")
	repeatCrawl := flag.Uint("r", 3, "The number of times to repeat each url.")
	numTabs := flag.Uint("t", 1, "Number of tabs that will crawl in parallel.")
	outPath := flag.String("o", "crawloutput", "Storage location for crawl results.")
	crawlUrl := flag.String("u", "", "Url to visit")
	flag.Parse()
	if len(*outPath) == 0 {
		panic("Please specify o")
	}
	if len(*crawlUrl) == 0 {
		panic("Please specify u")
	}

	// Setup crawl environment
	conf := Config{
		RepeatCrawl:    *repeatCrawl,
		OutputDir:      *outPath,
		Port:           *proxyPort,
		ShuffleUrls:    true,
		TakeScreenshot: true,
		NumTabs:        *numTabs,
	}
	conf.ProfileDir = path.Join(conf.OutputDir, "chrome_profile")
	conf.ScreenshotDir = path.Join(conf.OutputDir, "screenshots")
	if _, err := os.Stat(conf.OutputDir); os.IsNotExist(err) {
		os.MkdirAll(conf.OutputDir, 0755)
		os.MkdirAll(conf.ScreenshotDir, 0755)
	}

	// Open Logger
	if err := conf.OpenDefaultLogger(); err != nil {
		panic(err)
	}

	// Read list of urls to crawl

	conf.Logger.Println("Reading crawl list")
	if err := conf.ReadUrls(*crawlUrl); err != nil {
		panic(err)
	}

	// Start proxy
	conf.Logger.Println("Starting mitmproxy")
	network_dumpfile := path.Join(conf.OutputDir, "network.mproxy")
	proxy := exec.Command("mitmdump", "-p", fmt.Sprintf("%d", conf.Port), "-w", network_dumpfile)
	conf.Logger.Println(proxy.String())
	go proxy.Run()
	time.Sleep(5 * time.Second)
	defer proxy.Process.Kill()

	// Start Chrome browser
	conf.Logger.Println("Starting Chrome browser")
	browser, err := NewCrawler(conf)
	if err != nil {
		conf.Logger.Panic(err)
	}
	browser.Wait()

}
