<?php
/**
 * 页面头部模板
 *
 * @package Sysafari_Logistics
 */

if (!defined('ABSPATH')) {
    exit;
}
?>
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <link rel="profile" href="https://gmpg.org/xfn/11">
    
    <?php wp_head(); ?>
</head>

<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<div id="page" class="site">
    <a class="skip-link screen-reader-text" href="#primary"><?php esc_html_e('跳至内容', 'sysafari-logistics'); ?></a>

    <header class="site-header" role="banner">
        <!-- 顶部信息栏 -->
        <div class="header-top">
            <div class="container">
                <div class="header-top-left">
                    <span class="header-contact">
                        <i class="fas fa-phone-alt"></i>
                        <?php echo esc_html(sysafari_get_option('company_phone', '+86 400-XXX-XXXX')); ?>
                    </span>
                    <span class="header-email">
                        <i class="fas fa-envelope"></i>
                        <?php echo esc_html(sysafari_get_option('company_email', 'info@sysafari.com')); ?>
                    </span>
                </div>
                <div class="header-top-right">
                    <a href="<?php echo esc_url(home_url('/quote')); ?>" class="header-link">
                        <i class="fas fa-search-location"></i>
                        <?php esc_html_e('寻找服务据点', 'sysafari-logistics'); ?>
                    </a>
                    <span class="header-separator">|</span>
                    <div class="language-switcher">
                        <a href="?lang=zh" class="<?php echo (get_locale() == 'zh_CN') ? 'active' : ''; ?>">ZH</a>
                        <a href="?lang=en" class="<?php echo (get_locale() == 'en_US') ? 'active' : ''; ?>">EN</a>
                    </div>
                </div>
            </div>
        </div>

        <!-- 主导航区域 -->
        <div class="header-main">
            <div class="container">
                <!-- Logo -->
                <div class="site-logo">
                    <?php if (has_custom_logo()) : ?>
                        <?php the_custom_logo(); ?>
                    <?php else : ?>
                        <a href="<?php echo esc_url(home_url('/')); ?>">
                            <span class="logo-text"><?php echo esc_html(sysafari_get_option('company_name', 'Sysafari Logistics')); ?></span>
                        </a>
                    <?php endif; ?>
                </div>

                <!-- 主导航菜单 -->
                <nav class="main-navigation" role="navigation" aria-label="<?php esc_attr_e('主导航', 'sysafari-logistics'); ?>">
                    <?php
                    wp_nav_menu(array(
                        'theme_location' => 'primary',
                        'menu_id'        => 'primary-menu',
                        'menu_class'     => 'primary-menu',
                        'container'      => false,
                        'fallback_cb'    => 'sysafari_fallback_menu',
                    ));
                    ?>
                </nav>

                <!-- 右侧操作区域 -->
                <div class="header-actions">
                    <!-- 搜索框 -->
                    <div class="header-search">
                        <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>">
                            <input type="search" name="s" placeholder="<?php esc_attr_e('搜索', 'sysafari-logistics'); ?>" value="<?php echo get_search_query(); ?>">
                            <button type="submit" aria-label="<?php esc_attr_e('搜索', 'sysafari-logistics'); ?>">
                                <i class="fas fa-search"></i>
                            </button>
                        </form>
                    </div>

                    <!-- 客户登录 -->
                    <div class="header-login">
                        <?php if (is_user_logged_in()) : ?>
                            <a href="<?php echo esc_url(admin_url()); ?>" class="btn btn-outline">
                                <i class="fas fa-user"></i>
                                <?php esc_html_e('我的账户', 'sysafari-logistics'); ?>
                            </a>
                        <?php else : ?>
                            <a href="<?php echo esc_url(wp_login_url()); ?>" class="btn btn-outline">
                                <i class="fas fa-sign-in-alt"></i>
                                <?php esc_html_e('客户登录', 'sysafari-logistics'); ?>
                            </a>
                        <?php endif; ?>
                    </div>

                    <!-- 移动端菜单按钮 -->
                    <button class="mobile-menu-toggle" aria-label="<?php esc_attr_e('菜单', 'sysafari-logistics'); ?>" aria-expanded="false">
                        <span></span>
                        <span></span>
                        <span></span>
                    </button>
                </div>
            </div>
        </div>

        <!-- 移动端导航菜单 -->
        <div class="mobile-navigation" id="mobile-navigation">
            <div class="mobile-nav-inner">
                <?php
                wp_nav_menu(array(
                    'theme_location' => 'primary',
                    'menu_id'        => 'mobile-menu',
                    'menu_class'     => 'mobile-menu',
                    'container'      => false,
                ));
                ?>
                <div class="mobile-nav-footer">
                    <a href="<?php echo esc_url(home_url('/quote')); ?>" class="btn btn-primary btn-lg">
                        <?php esc_html_e('获取报价', 'sysafari-logistics'); ?>
                    </a>
                </div>
            </div>
        </div>
    </header>

    <main id="primary" class="site-main">
<?php

/**
 * 默认菜单（当未设置菜单时显示）
 */
function sysafari_fallback_menu() {
    ?>
    <ul class="primary-menu">
        <li><a href="<?php echo esc_url(home_url('/tracking')); ?>"><?php esc_html_e('追踪', 'sysafari-logistics'); ?></a></li>
        <li class="menu-item-has-children">
            <a href="<?php echo esc_url(home_url('/services')); ?>"><?php esc_html_e('寄件', 'sysafari-logistics'); ?></a>
        </li>
        <li><a href="<?php echo esc_url(home_url('/customer-service')); ?>"><?php esc_html_e('顾客服务', 'sysafari-logistics'); ?></a></li>
        <li><a href="<?php echo esc_url(home_url('/quote')); ?>"><?php esc_html_e('获取报价', 'sysafari-logistics'); ?></a></li>
        <li><a href="<?php echo esc_url(home_url('/about')); ?>"><?php esc_html_e('关于我们', 'sysafari-logistics'); ?></a></li>
        <li><a href="<?php echo esc_url(home_url('/contact')); ?>"><?php esc_html_e('联系我们', 'sysafari-logistics'); ?></a></li>
    </ul>
    <?php
}
