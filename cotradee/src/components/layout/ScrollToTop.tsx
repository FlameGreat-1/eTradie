import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * ScrollToTop is a utility component that resets the window scroll
 * position to (0, 0) whenever the route (pathname) changes.
 *
 * In Single Page Applications (SPAs), the browser does not
 * automatically scroll to the top on navigation because the
 * document technically remains the same. Mounting this at the
 * root of the App (outside the Routes) ensures that clicking
 * any footer link or sidebar item always lands the user at
 * the top of the new surface.
 */
export default function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    // We use 'instant' behavior here. While 'smooth' looks nice,
    // it can be jarring during a page transition where the old
    // content is being swapped for new content. 'instant' ensures
    // the user is at the top before the new page paints.
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: 'instant',
    });
  }, [pathname]);

  return null;
}
