package main

/*
 * Copyright 2020 Floor Terra
 *
 * Permission to use, copy, modify, and/or distribute this software for
 * any purpose with or without fee is hereby granted, provided that the
 * above copyright notice and this permission notice appear in all
 * copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND ISC DISCLAIMS ALL WARRANTIES WITH
 * REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL ISC BE LIABLE FOR ANY
 * SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
 * OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

import (
	"context"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os/exec"
	"path"
	"sync"
	"time"

	"github.com/chromedp/chromedp"
)

type Crawler struct {
	Config         Config
	UrlChan        chan Url
	ActiveBrowsers *sync.WaitGroup
}

func NewCrawler(config Config) (crawler *Crawler, err error) {
	crawler = new(Crawler)
	crawler.Config = config
	crawler.UrlChan = make(chan Url)
	crawler.ActiveBrowsers = &sync.WaitGroup{}
	for i := 0; i < int(crawler.Config.NumTabs); i++ {
		crawler.ActiveBrowsers.Add(1)
		go crawler.AddBrowser(fmt.Sprintf("%s-%02d", crawler.Config.ProfileDir, i))
	}

	go crawler.feedurls()
	return crawler, nil
}

func (c *Crawler) AddBrowser(profiledir string) {
	c.Config.Logger.Println("Adding browser")
	options := []chromedp.ExecAllocatorOption{
		chromedp.NoFirstRun,
		chromedp.NoDefaultBrowserCheck,
		chromedp.Headless,

		chromedp.Flag("disable-background-networking", true),
		chromedp.Flag("enable-features", "NetworkService,NetworkServiceInProcess"),
		chromedp.Flag("disable-background-timer-throttling", true),
		chromedp.Flag("disable-backgrounding-occluded-windows", true),
		chromedp.Flag("disable-breakpad", true),
		chromedp.Flag("disable-client-side-phishing-detection", true),
		chromedp.Flag("disable-default-apps", true),
		chromedp.Flag("disable-dev-shm-usage", true),
		chromedp.Flag("disable-extensions", true),
		chromedp.Flag("disable-features", "site-per-process,TranslateUI,BlinkGenPropertyTrees"),
		chromedp.Flag("disable-hang-monitor", true),
		chromedp.Flag("disable-ipc-flooding-protection", true),
		chromedp.Flag("disable-popup-blocking", true),
		chromedp.Flag("disable-prompt-on-repost", true),
		chromedp.Flag("disable-renderer-backgrounding", true),
		chromedp.Flag("disable-sync", true),
		chromedp.Flag("force-color-profile", "srgb"),
		chromedp.Flag("metrics-recording-only", true),
		chromedp.Flag("safebrowsing-disable-auto-update", true),
		chromedp.Flag("enable-automation", true),
		chromedp.Flag("password-store", "basic"),
		chromedp.Flag("use-mock-keychain", true),
		chromedp.Flag("guest", true), // Browse Without Sign-in
		chromedp.ProxyServer(fmt.Sprintf("127.0.0.1:%d", c.Config.Port)),
		chromedp.Flag("user-data-dir", profiledir),
		chromedp.Flag("disable-http2", true), // Mitmproxy doesn't work well with HTTP2
	}

	ctx, cancel := chromedp.NewExecAllocator(context.Background(), options...)
	defer cancel()
	ctx, cancel = chromedp.NewContext(ctx)
	defer cancel()
	time.Sleep(1 * time.Second)

	if err := chromedp.Run(ctx); err != nil {
		c.Config.Logger.Println(err.Error())
		go func() {
			time.Sleep(5 * time.Second)
			c.AddBrowser(profiledir)
		}()
		return
	}

	chromedp.Run(ctx, chromedp.Navigate("https://mitm.it/"))
	time.Sleep(2 * time.Second)
	// Make sure the mitmproxy certificates are trusted
	trustCmd := exec.Command("certutil", "-d", "sql:/root/.pki/nssdb", "-A", "-t", "TC", "-n", "\"mitmproxy\"", "-i", "/root/.mitmproxy/mitmproxy-ca.pem")
	err := trustCmd.Run()
	if err != nil {
		panic(err)
	}

	var screenshot_data []byte
	for url := range c.UrlChan {
		c.Config.Logger.Println(profiledir, url.Id, url.Url)
		if err := chromedp.Run(ctx, chromedp.Navigate(url.Url)); err != nil {
			c.Config.Logger.Println(err.Error())
			go func() {
				time.Sleep(5 * time.Second)
				c.AddBrowser(profiledir)
			}()
			return
		}
		time.Sleep(5 * time.Second)
		if c.Config.TakeScreenshot {
			// Take screenshot
			if err := chromedp.Run(ctx, chromedp.CaptureScreenshot(&screenshot_data)); err != nil {
				c.Config.Logger.Println(err.Error())
				go func() {
					time.Sleep(5 * time.Second)
					c.AddBrowser(profiledir)
				}()
				return
			}
			if len(screenshot_data) > 0 {
				if err := ioutil.WriteFile(path.Join(c.Config.ScreenshotDir, fmt.Sprintf("%s.png", time.Now().Format("2006-01-02_150405"))), screenshot_data, 0755); err != nil {
					c.Config.Logger.Println(err.Error())
					go func() {
						time.Sleep(5 * time.Second)
						c.AddBrowser(profiledir)
					}()
					return
				}
			}
		}
	}

	c.ActiveBrowsers.Done()
}

func (c Crawler) feedurls() {
	for n := uint(0); n < c.Config.RepeatCrawl; n++ {
		if c.Config.ShuffleUrls {
			rand.Shuffle(len(c.Config.Urls), func(i, j int) {
				c.Config.Urls[i], c.Config.Urls[j] = c.Config.Urls[j], c.Config.Urls[i]
			})
			for url := range c.Config.Urls {
				c.UrlChan <- c.Config.Urls[url]
			}
		}

	}
	close(c.UrlChan)
}

func (c Crawler) Wait() {
	c.ActiveBrowsers.Wait()
}
